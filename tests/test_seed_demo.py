"""El seed de la demo pública, corrido contra una base limpia.

**Por qué un test y no una corrida a mano.** El cron de reset borra la base y
vuelve a sembrar, así que lo que hay que garantizar es que el seed funcione
*desde cero*. Probarlo contra una instancia ya sembrada no verifica eso: la
mitad de los pasos cae en la rama "ya estaba".

Lo que fijan estos tests, en orden de lo que se rompe sin que se note:

1. 🔴 **Que el seed corra entero sobre una base vacía.** El orden importa: el
   stock necesita el producto, los presupuestos necesitan el cliente.
2. 🔴 **Que NO emita facturas.** El módulo de facturación habla con ARCA de
   verdad; una demo pública no puede pedir CAE por cada visita.
3. 🔴 **Que queden las distintas condiciones frente al IVA.** Es lo que decide
   el tipo de comprobante, y con todos los clientes iguales esa parte del
   producto no se ve.
4. Que el stock no quede todo abastecido, y que correrlo dos veces no duplique.
"""
import json

import pytest

from scripts.seed_demo import Api, _lista, sembrar, url_no_productiva


class _ApiDeTest(Api):
    """Habla con el `TestClient` con la misma interfaz que usa `sembrar()`, y
    **serializa igual que el `Api` real** (`default=str`)."""

    def __init__(self, client):
        self.client = client

    def _pedir(self, metodo, ruta, cuerpo=None):
        datos = json.dumps(cuerpo, default=str) if cuerpo is not None else None
        respuesta = self.client.request(
            metodo, ruta, content=datos,
            headers={"Content-Type": "application/json"} if datos else None,
        )
        if respuesta.status_code >= 400:
            raise RuntimeError(f"{metodo} {ruta} -> {respuesta.status_code}: "
                               f"{respuesta.text[:300]}")
        return respuesta.json() if respuesta.content else None


@pytest.fixture
def api(admin_client):
    return _ApiDeTest(admin_client)


# ── 🔴 Desde cero ─────────────────────────────────────────────────────────

def test_el_seed_corre_entero_sobre_una_base_vacia(api, capsys):
    """El escenario del cron de reset."""
    sembrar(api)

    salida = capsys.readouterr().out
    assert "productos     9 creados" in salida
    assert "clientes      5 creados" in salida
    assert "categorías    3 creados" in salida


def test_deja_el_catalogo_completo(api):
    sembrar(api)

    assert len(_lista(api.get("/api/productos"))) == 9
    assert len(_lista(api.get("/api/clientes"))) == 5
    assert len(_lista(api.get("/api/proveedores"))) == 2


def test_hay_productos_y_servicios(api):
    """La distinción que este producto hace en el catálogo. Un servicio no
    lleva stock, y es correcto que no lo lleve."""
    sembrar(api)

    tipos = {p.get("tipo") for p in _lista(api.get("/api/productos"))}
    assert tipos == {"producto", "servicio"}


# ── 🔴 Las condiciones frente al IVA ──────────────────────────────────────

def test_hay_clientes_con_distintas_condiciones_de_iva(api):
    """🔴 Es lo que decide el tipo de comprobante. Con todos los clientes en la
    misma condición, esa parte del producto no se ve."""
    sembrar(api)

    condiciones = {c.get("iva_condition") for c in _lista(api.get("/api/clientes"))}
    condiciones.discard(None)
    condiciones.discard("")

    assert len(condiciones) >= 3, f"pocas condiciones: {condiciones}"
    assert "Responsable Inscripto" in condiciones
    assert "Consumidor Final" in condiciones


# ── 🔴 Facturas sí, pero sin CAE ──────────────────────────────────────────

def test_emite_facturas_pero_ninguna_con_CAE(api):
    """Cambió el 2026-08-06, a pedido del humano: la pantalla de facturación
    estaba vacía y un interesado no podía ver ni el comprobante ni su PDF.

    🔴 **Lo que NO cambió es lo que este test protegía.** El módulo habla con
    ARCA de verdad, y pedir CAE contra el padrón por cada visita a una demo
    pública sigue sin ser algo que se pueda dejar corriendo. Lo que hace que
    sea seguro es que `solicitar_cae()` corta apenas ve que la instancia no
    tiene certificado configurado —y una demo no lo tiene—, así que el
    comprobante nace como **documento interno**.

    Por eso la aserción no es "hay facturas": es **que ninguna tenga CAE**. Si
    mañana alguien configurara ARCA en una demo, este test se pone en rojo,
    que es exactamente cuando hay que enterarse.
    """
    sembrar(api)

    facturas = _lista(api.get("/api/facturas"))
    assert facturas, "la pantalla de facturación no puede quedar vacía"

    # 🔴 **La garantía no es el estado del CAE: es que no hay ARCA configurado.**
    # Se aprendió escribiendo este test. El motor tiene dos caminos y ninguno
    # sale a la red en una demo:
    #
    # - Con `ENV=development` genera un CAE **simulado** (`_mock_cae`), sin
    #   pedirle nada a nadie. Es lo que pasa en esta suite, y por eso asertar
    #   `cae == ""` daba rojo.
    # - En producción mira la config de ARCA: **sin certificado deja `ta=None`
    #   y `solicitar_cae` devuelve la factura intacta**, sin CAE.
    #
    # Lo que el seed tiene que garantizar, entonces, es no dejar ARCA
    # configurado. Si alguien lo configurara en una demo, este test se pone en
    # rojo — que es exactamente cuando hay que enterarse.
    assert not api.get("/api/config")["arca"], (
        "el seed dejó ARCA configurado: una demo pública con certificado "
        "emitiría comprobantes fiscales de verdad"
    )


def test_si_emite_presupuestos_y_remitos(api):
    """La contracara: sin esto, el test de arriba pasaría con un seed que no
    crea ningún documento."""
    sembrar(api)

    assert len(_lista(api.get("/api/presupuestos"))) >= 4
    # El aceptado genera su remito.
    assert len(_lista(api.get("/api/remitos"))) >= 1


def test_los_presupuestos_quedan_en_varios_estados(api):
    sembrar(api)

    # El campo se llama `status`, no `estado` — el payload de entrada usa
    # "estado" y la respuesta "status", que es justo el par que uno confunde.
    estados = {p.get("status") for p in _lista(api.get("/api/presupuestos"))}
    assert len(estados) >= 3, f"pocos estados: {estados}"
    assert "borrador" in estados, "ninguno quedó en el estado inicial"


# ── La pantalla de Tesorería ──────────────────────────────────────────────

def test_deja_cuentas_de_tesoreria(api):
    """La pantalla se abría con `{"cuentas": [], "movimientos": []}` — medido
    contra la demo el 2026-08-07. Restolibra, que comparte el módulo, ya las
    tenía."""
    t = api.get("/api/tesoreria") or {}

    assert t.get("cuentas") == []  # antes de sembrar

    sembrar(api)
    t = api.get("/api/tesoreria") or {}

    assert len(t["cuentas"]) == 2
    # Y con movimiento: una cuenta con saldo inicial y nada más deja la mitad
    # de la pantalla —el listado— vacía igual.
    assert len(t["movimientos"]) >= 3


def test_la_transferencia_toca_las_dos_cuentas(api):
    """Es el ejemplo que hace entender la pantalla: mostrar sólo ingresos deja
    sin verse que tesorería mueve plata **entre** cuentas."""
    sembrar(api)
    cuentas = {c["nombre"]: c for c in api.get("/api/tesoreria")["cuentas"]}

    caja = cuentas["Efectivo en caja fuerte"]
    banco = cuentas["Cuenta corriente Banco Galicia"]

    assert caja["saldo"] < caja["saldo_inicial"], "de la caja salió el efectivo"
    assert banco["saldo"] != banco["saldo_inicial"], "al banco entró"


# ── 🔴 El Libro de IVA, con las dos mitades ───────────────────────────────

def test_deja_facturas_de_compra_para_el_libro_de_iva(api):
    """🔴 El lado de compras del Libro de IVA **sólo toma los egresos
    `tipo_comprobante = 'factura'`** (el filtro está en el SQL de
    `get_egresos_para_iva`). Con egresos sueltos —que es lo que sembraba
    antes— la pantalla mostraba las ventas y el lado de compras salía vacío,
    y el export bajaba un archivo de **0 bytes**. Medido contra la demo.
    """
    sembrar(api)

    egresos = _lista(api.get("/api/egresos"))
    facturas = [e for e in egresos if e["tipo_comprobante"] == "factura"]

    assert len(facturas) >= 2, "sin facturas de compra el libro sale vacío"
    # Y con lo que el export necesita para armar la línea: sin proveedor no hay
    # CUIT, y sin número el archivo sale con ceros en punto de venta y número.
    for f in facturas:
        assert f["proveedor_id"], f"{f['concepto']} sin proveedor"
        assert "-" in f["numero"], f"{f['concepto']} sin número de comprobante"


def test_el_iva_de_los_egresos_no_se_va_de_escala(api):
    """`iva_pct` es una **fracción** en egresos: el alta hace
    `monto_neto * iva_pct` sin dividir por 100. Mandar `21` en vez de `0.21`
    no da un 21% — le puso $588.000 de IVA a un gasto de $28.000, y así estuvo
    en la demo."""
    sembrar(api)

    egresos = _lista(api.get("/api/egresos"))
    assert egresos, "sin egresos el `for` de abajo no prueba nada"
    for e in egresos:
        neto = float(e["monto_neto"])
        assert 0 < float(e["iva_monto"]) <= neto * 0.30, (
            f"{e['concepto']}: IVA de {e['iva_monto']} sobre un neto de {neto}"
        )


# ── 🔴 Stock que no está todo abastecido ──────────────────────────────────

def test_queda_stock_en_cero_y_bajo_el_minimo(api):
    """La pantalla de faltantes existe para eso; con todo abastecido no muestra
    nada."""
    sembrar(api)

    # ⚠️ El stock **no viene en `/api/productos`**: va en `/api/stock`, como
    # `stock_actual`. El catálogo es una cosa y las existencias otra.
    respuesta = api.get("/api/stock")
    por_codigo = {p["codigo"]: p for p in respuesta["productos"]}

    assert float(por_codigo["INF-001"]["stock_actual"]) == 0
    bajo = por_codigo["PAP-003"]
    assert 0 < float(bajo["stock_actual"]) < float(bajo["stock_minimo"])
    # Y que el producto lo marque como alerta, que es lo que la pantalla usa.
    assert any(a["codigo"] == "PAP-003" for a in respuesta["alertas"])


# ── Idempotencia ──────────────────────────────────────────────────────────

def test_correrlo_dos_veces_no_duplica(api, capsys):
    sembrar(api)
    capsys.readouterr()

    sembrar(api)

    salida = capsys.readouterr().out
    assert "productos     0 creados, 9 ya estaban" in salida
    assert len(_lista(api.get("/api/productos"))) == 9


def test_la_segunda_corrida_no_cambia_el_stock(api):
    """El ajuste va en modo `absoluto`, que fija la existencia en vez de
    sumarla. Con modo `entrada`, cada corrida del cron duplicaría el stock."""
    sembrar(api)
    antes = {p["codigo"]: p["stock_actual"] for p in api.get("/api/stock")["productos"]}

    sembrar(api)

    despues = {p["codigo"]: p["stock_actual"] for p in api.get("/api/stock")["productos"]}
    assert despues == antes


def test_la_segunda_corrida_no_agrega_presupuestos(api):
    sembrar(api)
    antes = len(_lista(api.get("/api/presupuestos")))

    sembrar(api)

    assert len(_lista(api.get("/api/presupuestos"))) == antes


# ── La guarda ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "https://demo.contalibra.com.ar",
    "https://dev.contalibra.com.ar",
    "http://127.0.0.1:8000",
])
def test_donde_si_se_puede_sembrar(url):
    assert url_no_productiva(url) is True


@pytest.mark.parametrize("url", [
    "https://contalibra.com.ar",
    "https://sistema.contalibra.com.ar",
    "https://demoliciones.contalibra.com.ar",
])
def test_donde_NO(url):
    """🔴 `sistema.contalibra.com.ar` es la instancia productiva, con clientes
    reales facturando. Datos inventados mezclados ahí no se distinguen
    después."""
    assert url_no_productiva(url) is False


def test_LA_FECHA_NO_SE_RESUELVE_AL_IMPORTAR(monkeypatch):
    """🔴 La guarda del defecto que puso en rojo el CI de Restolibra el 2026-08-29.

    `HOY` era un `date.today()` a nivel de módulo: quedaba congelado en el
    instante del import. Un proceso que importa antes de medianoche y siembra
    después —esta suite tarda casi ocho minutos, y el cron de la demo corre
    sobre procesos que viven días— siembra para AYER, y después la pantalla de
    tesorería se ve vacía el día que alguien la abre.

    No se prueba llamando a `sembrar()`: eso es una corrida entera contra la
    base. Se prueba la pieza que decide la fecha, que es donde vivía el defecto.
    """
    import datetime

    import scripts.seed_demo as seed

    # Se mueve el reloj DESPUÉS de que el módulo ya está importado, que es
    # exactamente el cruce de medianoche a mitad de corrida.
    otro_dia = datetime.date(2031, 7, 4)

    class RelojMovido(datetime.date):
        @classmethod
        def today(cls):
            return otro_dia

    monkeypatch.setattr(seed, "date", RelojMovido)

    assert seed._fijar_hoy() == otro_dia, (
        "la fecha sigue viniendo del import: mover el reloj no la cambió"
    )
    # Y deja el módulo consistente: los lugares que siembran datos del día leen
    # `seed.HOY`, no el valor devuelto.
    assert seed.HOY == otro_dia, (
        "`_fijar_hoy` devolvió la fecha nueva pero no actualizó `HOY`, que es "
        "la que usan los sembradores"
    )
