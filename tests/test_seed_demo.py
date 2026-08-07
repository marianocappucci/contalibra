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
