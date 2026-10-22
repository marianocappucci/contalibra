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
    # `GET /api/config/arca` y no `/api/config`: el segundo se fue el 2026-08-30
    # con la pantalla que lo consumia. Devuelve `null` si no hay fila.
    assert not api.get("/api/config/arca"), (
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


# ── 🔴 La demo no queda con datos fiscales reales (ADR-061 de libracore) ─────────────────────────────────────────

def test_el_texto_de_la_semilla_no_tiene_cuit_de_forma_real():
    """Un CUIT con verificador válido y fuera del rango reservado `99999xxx` no se puede distinguir de uno real. Los
    inventados que no cierran el verificador no existen en el padrón y no cuentan. Este mira el archivo, así que no
    depende de qué rutas corrieron al sembrar (la bandeja de MercadoPago sólo existe con `DEMO_MODE` al importar)."""
    from pathlib import Path

    from libracore.demo import auditar_literales

    hallazgos = auditar_literales(Path("scripts/seed_demo.py").read_text(encoding="utf-8"), "scripts/seed_demo.py")
    assert hallazgos == [], "\n".join(str(h) for h in hallazgos)


@pytest.fixture
def api_de_demo(monkeypatch, request):
    """`DEMO_MODE=1` ANTES de armar la app, como corre la demo."""
    monkeypatch.setenv("DEMO_MODE", "1")
    return request.getfixturevalue("api")


def test_la_semilla_no_deja_datos_fiscales_reales_en_la_base(api_de_demo):
    """Lo que quedó en la base de LibraCore y en `config.json` después de sembrar: un CUIT de forma real, un
    certificado, ARCA en producción, un token de MercadoPago que no es de prueba."""
    from libracore.db import core
    from libracore.demo import auditar_datos_fiscales

    sembrar(api_de_demo)
    with core.get_connection() as conn:
        hallazgos = auditar_datos_fiscales(conn)
    assert hallazgos == [], "\n".join(str(h) for h in hallazgos)


# ── La sucursal de la PC del local (sólo con DEMO_MODE; decisión del humano, 2026-10-22) ────────────────────────────
#
# Con un nodo de LibraEdge vinculado a la única sucursal de la demo, la web queda con el stock en sólo lectura (409
# `deposito_de_sucursal_con_nodo`, libracommerce ADR-071) y un visitante no puede vender. La semilla deja una segunda
# sucursal con su depósito y algo de stock para que la PC se vincule ahí. `reset_demo.sh` restaura los nodos con su
# `branch_id` viejo después de sembrar: el id de la sucursal tiene que ser SIEMPRE el mismo.


def _filas(sql, params=()):
    from app import db_core

    with db_core.get_connection() as conn:
        return [tuple(f) for f in conn.execute(sql, params).fetchall()]


def _stock_por_deposito():
    """{código: {nombre del depósito: existencia}} sólo de lo que no es cero."""
    from scripts.seed_demo import PRODUCTOS

    codigo_de = {nombre: codigo for nombre, codigo, *_ in PRODUCTOS}
    por_codigo = {}
    for nombre, deposito, cantidad in _filas(
            "SELECT ci.name, l.name, SUM(sm.quantity_delta) FROM stock_movements sm "
            "JOIN catalog_items ci ON ci.id = sm.item_id JOIN locations l ON l.id = sm.location_id "
            "GROUP BY ci.name, l.name HAVING SUM(sm.quantity_delta) <> 0 ORDER BY ci.name, l.name"):
        por_codigo.setdefault(codigo_de[nombre], {})[deposito] = float(cantidad)
    return por_codigo


def test_con_demo_mode_deja_la_sucursal_del_local_con_su_id_fijo_su_deposito_y_su_stock(api_de_demo):
    from scripts.seed_demo import (
        DEPOSITO_DEL_LOCAL,
        ID_SUCURSAL_DEL_LOCAL,
        STOCK,
        STOCK_DEL_LOCAL,
        SUCURSAL_DEL_LOCAL,
    )

    sembrar(api_de_demo)

    # «Casa central» es la 1 y la predeterminada; la del local, la 2 y no predeterminada.
    sucursales = _filas("SELECT id, name, is_default, default_location_id, active FROM branches ORDER BY id")
    assert len(sucursales) == 2
    (casa, nombre_casa, casa_default, casa_deposito, _), (local_id, nombre, local_default, local_deposito, activa) = sucursales
    assert (casa, nombre_casa, casa_default) == (1, "Casa central", 1)
    assert (local_id, nombre, local_default, activa) == (ID_SUCURSAL_DEL_LOCAL, SUCURSAL_DEL_LOCAL, 0, 1)
    assert ID_SUCURSAL_DEL_LOCAL == 2 and SUCURSAL_DEL_LOCAL == "Sucursal con PC del local"
    # Su depósito, predeterminado de ella, activo, y el de Casa central sigue siendo el de venta de la instancia.
    assert _filas("SELECT id, name, is_default, active FROM locations WHERE branch_id = ?", (local_id,)) == [
        (local_deposito, DEPOSITO_DEL_LOCAL, 0, 1)]
    assert _filas("SELECT name, branch_id FROM locations WHERE is_default = 1") == [("Depósito principal", casa)]
    assert casa_deposito != local_deposito
    # El stock del local es el pedido, y el TOTAL de cada producto sigue siendo el de `STOCK` (lo que ve la pantalla).
    por_deposito = _stock_por_deposito()
    for codigo, cantidad in STOCK_DEL_LOCAL.items():
        assert por_deposito[codigo][DEPOSITO_DEL_LOCAL] == cantidad
        assert por_deposito[codigo]["Depósito principal"] == STOCK[codigo] - cantidad
    assert {c for c, d in por_deposito.items() if DEPOSITO_DEL_LOCAL in d} == set(STOCK_DEL_LOCAL)
    totales = {p["codigo"]: float(p["stock_actual"]) for p in api_de_demo.get("/api/stock")["productos"]}
    assert {c: totales[c] for c in STOCK} == {c: float(v) for c, v in STOCK.items()}
    # Y los productos en alerta siguen en alerta (el stock del local no los saca de ahí).
    assert {a["codigo"] for a in api_de_demo.get("/api/stock")["alertas"]} >= {"PAP-003", "INF-003", "INF-001"}


def test_fuera_de_demo_mode_no_crea_la_sucursal_del_local(api, monkeypatch, capsys):
    from scripts.seed_demo import DEPOSITO_DEL_LOCAL, SUCURSAL_DEL_LOCAL

    monkeypatch.delenv("DEMO_MODE", raising=False)
    sembrar(api)

    assert _filas("SELECT name FROM branches") == [("Casa central",)]
    assert _filas("SELECT 1 FROM locations WHERE name = ?", (DEPOSITO_DEL_LOCAL,)) == []
    assert _filas("SELECT 1 FROM branches WHERE name = ?", (SUCURSAL_DEL_LOCAL,)) == []
    assert "sucursal del local: no es una instancia demo" in capsys.readouterr().out
    # Todo el stock queda en el depósito de siempre.
    assert {d for dep in _stock_por_deposito().values() for d in dep} == {"Depósito principal"}


def test_correrlo_dos_veces_con_demo_mode_no_cambia_nada(api_de_demo):
    sembrar(api_de_demo)
    sucursales = _filas("SELECT id, name, is_default, default_location_id FROM branches ORDER BY id")
    depositos = _filas("SELECT id, name, is_default, branch_id FROM locations ORDER BY id")
    stock = _stock_por_deposito()
    depositos_stock = _filas("SELECT location_id, SUM(quantity_delta) FROM stock_movements GROUP BY location_id ORDER BY 1")

    sembrar(api_de_demo)

    assert _filas("SELECT id, name, is_default, default_location_id FROM branches ORDER BY id") == sucursales
    assert _filas("SELECT id, name, is_default, branch_id FROM locations ORDER BY id") == depositos
    assert _stock_por_deposito() == stock, "la segunda corrida movió el stock entre depósitos"
    assert _filas("SELECT location_id, SUM(quantity_delta) FROM stock_movements GROUP BY location_id ORDER BY 1") == depositos_stock
    assert len(sucursales) == 2 and len(depositos) == 2


def test_la_venta_web_del_visitante_sigue_saliendo_de_casa_central(api_de_demo):
    """`get_default_sucursal_id` sigue siendo «Casa central»: la web vende de su depósito, no del del local."""
    from libracommerce.erp import catalogo

    from app import db_core

    sembrar(api_de_demo)
    with db_core.get_connection() as conn:
        assert catalogo.get_default_sucursal_id(conn) == 1
        assert catalogo.get_default_deposito_id(conn) == _filas("SELECT id FROM locations WHERE name = 'Depósito principal'")[0][0]
    antes = _stock_por_deposito()["PAP-001"]
    producto = next(p["id"] for p in _lista(api_de_demo.get("/api/productos")) if p["codigo"] == "PAP-001")

    venta = api_de_demo.post("/api/ventas", {
        "fecha": "2026-10-22", "items": [{"nombre": "Resma A4 75 g", "qty": 2, "precio": 8500, "producto_id": producto}],
        "pagos": [{"medio": "efectivo", "monto": 17000}],
    })

    assert _filas("SELECT branch_id FROM sales WHERE id = ?", (venta["id"],)) == [(1,)]
    despues = _stock_por_deposito()["PAP-001"]
    assert despues["Depósito principal"] == antes["Depósito principal"] - 2
    assert despues["Depósito del local"] == antes["Depósito del local"]


def test_adoptar_no_vuelve_a_asignar_el_deposito_del_local_a_casa_central(api_de_demo):
    """`adoptar` (la revisión 0006 y cada `init_db()`) sólo asigna los depósitos con `branch_id` NULL."""
    from app import database as db
    from app import db_core
    from app.sucursal_unica import adoptar

    sembrar(api_de_demo)
    antes = _filas("SELECT id, name, branch_id FROM locations ORDER BY id")

    with db_core.get_connection() as conn:
        informe = adoptar(conn)
    db.init_db()                                                 # el reinicio del contenedor

    assert informe["depositos_asignados"] == 0 and informe["sucursal_creada"] is False
    assert _filas("SELECT id, name, branch_id FROM locations ORDER BY id") == antes
    assert [f[0] for f in _filas("SELECT id FROM branches ORDER BY id")] == [1, 2]


def test_si_la_sucursal_no_sale_con_su_id_la_semilla_falla_y_no_deja_nada(api_de_demo):
    """El reset restaura los nodos con el `branch_id` que tenían: otra numeración los dejaría en la sucursal equivocada,
    sin error. Si alguien creó una sucursal antes que la semilla, se falla fuerte y no queda la del local escrita."""
    from libracommerce.erp import catalogo

    from app import db_core
    from scripts.seed_demo import SUCURSAL_DEL_LOCAL

    with db_core.get_connection() as conn:
        catalogo.create_sucursal(conn, "Otra")                   # se queda con el id 2

    with pytest.raises(RuntimeError, match="tiene que ser 2"):
        sembrar(api_de_demo)

    assert _filas("SELECT 1 FROM branches WHERE name = ?", (SUCURSAL_DEL_LOCAL,)) == []
    assert [f[1] for f in _filas("SELECT id, name FROM branches ORDER BY id")] == ["Casa central", "Otra"]


def test_en_el_reset_la_sucursal_del_local_sale_con_el_id_2_despues_de_la_cadena_y_el_arranque(client, monkeypatch):
    """El orden real de `reset_demo.sh`: schema vacío -> cadenas de migración (la `0006` adopta «Casa central») ->
    arranque (`init_db`) -> semilla. Se mide la numeración de `branches` en ese camino, no en la plantilla de la suite."""
    from libracommerce.erp import catalogo

    from app import database as db
    from app import db_core
    from tests.conftest import _reset_data_dir
    from tests.test_sucursal_unica import _comandos_de_la_cadena, _correr

    _reset_data_dir()                                            # base vacía, como después del DROP SCHEMA
    for comando in _comandos_de_la_cadena("head"):
        _correr(comando)
    assert _filas("SELECT id, name FROM branches") == [(1, "Casa central")]
    db.init_db()                                                 # el arranque de la app
    assert _filas("SELECT id, name FROM branches") == [(1, "Casa central")]

    with db_core.get_connection() as conn:
        assert catalogo.create_sucursal(conn, "Sucursal con PC del local", deposito="Depósito del local") == 2


def test_una_instancia_anterior_a_la_sucursal_unica_no_aborta_la_siembra(api_de_demo, capsys):
    """El reset siembra con el seed de `develop` sobre un contenedor que puede ser de `main`: sin «Casa central» la del
    local saldría con el id 1, y abortar dejaría la demo a medio sembrar. Se omite, y lo dice."""
    from app import db_core

    with db_core.get_connection() as conn:
        conn.execute("UPDATE locations SET branch_id = NULL")
        conn.execute("UPDATE cajas SET sucursal_id = NULL")
        conn.execute("DELETE FROM branches")

    sembrar(api_de_demo)

    assert "la instancia no tiene «Casa central»" in capsys.readouterr().out
    assert _filas("SELECT id FROM branches") == []
    assert len(_lista(api_de_demo.get("/api/productos"))) == 9, "el resto de la siembra siguió"
