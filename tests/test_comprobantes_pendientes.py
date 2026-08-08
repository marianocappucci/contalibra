"""La bandeja de comprobantes pendientes montada en Contalibra.

El mecanismo entero (idempotencia, agrupado, estados) tiene su suite en
LibraCore. Lo que se prueba acá es lo que **sólo se puede probar en el
producto**: que los dos gates queden bien puestos, y el circuito completo
—depositar, prefillear, emitir, quedar marcado— contra el camino de emisión
real.

Con `ENV=development` libracore usa numeración local y CAE simulado, así que la
factura se emite de verdad sin tocar ARCA ni la red. Eso importa: marcar el
pendiente pasa **después** del CAE, y un test que no llegue a emitir no ejerce
esa línea.
"""
import datetime

from libraauth.session_auth import SERVICE_TOKEN_ENV, SERVICE_TOKEN_HEADER

HOY = datetime.date.today().isoformat()
TOKEN = "un-token-de-servicio-de-prueba"

BANDEJA = "/api/comprobantes-pendientes"


def _payload(**extra):
    payload = {
        "origen_producto": "libradesk",
        "origen_instancia": "compulibra",
        "origen_tipo": "cuota_contrato",
        "origen_id": "42",
        "cliente_razon": "Ferretería San Martín",
        "cliente_cuit": "30-71234567-9",
        "periodo_desde": "2026-08-01",
        "periodo_hasta": "2026-08-31",
        "items": [{"description": "Alquiler impresora — agosto", "qty": 1,
                   "unit_price": 45000.0, "iva_rate": 0.21}],
    }
    payload.update(extra)
    return payload


def _depositar(client, **extra):
    """Deposita como lo haría LibraDesk: con el token de servicio, sin sesión."""
    return client.post(BANDEJA, json=_payload(**extra),
                       headers={SERVICE_TOKEN_HEADER: TOKEN})


# ── Los gates ────────────────────────────────────────────────────────────────

def test_sin_la_variable_el_token_no_deposita(client, monkeypatch):
    """La garantía de adopción, igual que en `test_token_de_servicio`: una
    instancia que actualiza y no toca su compose no queda con un endpoint
    nuevo abierto."""
    monkeypatch.delenv(SERVICE_TOKEN_ENV, raising=False)
    assert _depositar(client).status_code in (401, 403)


def test_con_la_variable_el_token_deposita(client, monkeypatch):
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    r = _depositar(client)
    assert r.status_code == 201, r.text
    assert r.json()["creado"] is True


def test_un_token_equivocado_no_deposita(client, monkeypatch):
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    r = client.post(BANDEJA, json=_payload(),
                    headers={SERVICE_TOKEN_HEADER: "otro-token"})
    assert r.status_code in (401, 403)


def test_la_bandeja_pide_sesion(client, monkeypatch):
    """Control negativo: el token que deposita **no** abre la bandeja. Si esto
    diera 200, el token de un producto alcanzaría para descartar o facturar lo
    que otro depositó."""
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    r = client.get(BANDEJA, headers={SERVICE_TOKEN_HEADER: TOKEN})
    assert r.status_code in (401, 403)


def test_un_admin_logueado_ve_la_bandeja(admin_client):
    r = admin_client.get(BANDEJA)
    assert r.status_code == 200
    assert r.json()["total_pendientes"] == 0


# ── El circuito completo ─────────────────────────────────────────────────────

def test_de_la_bandeja_a_la_factura_emitida(admin_client, monkeypatch):
    """El circuito que justifica todo el módulo, de punta a punta."""
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)

    # 1. LibraDesk deposita dos cuotas del mismo cliente.
    uno = _depositar(admin_client, origen_id="1").json()["id"]
    dos = _depositar(admin_client, origen_id="2", periodo_desde="2026-07-01",
                     periodo_hasta="2026-07-31").json()["id"]
    assert admin_client.get(BANDEJA).json()["total_pendientes"] == 2

    # 2. La persona elige facturarlas juntas y ve el formulario.
    prefill = admin_client.post(f"{BANDEJA}/facturar-prefill",
                                json={"ids": [uno, dos]})
    assert prefill.status_code == 200, prefill.text
    prefill = prefill.json()
    assert len(prefill["items"]) == 2
    assert prefill["fch_serv_desde"] == "2026-07-01"
    assert prefill["comprobantes_ids"] == [uno, dos]

    # Mirar el formulario no facturó nada todavía.
    assert admin_client.get(BANDEJA).json()["total_pendientes"] == 2

    # 3. Emite, con el camino de emisión de siempre.
    factura = admin_client.post("/api/facturas", json={
        "tipo": 11,
        "fecha": HOY,
        "client_name": prefill["client_name"],
        "condicion_venta": prefill["condicion_venta"],
        "items": prefill["items"],
        "comprobantes_pendientes_ids": prefill["comprobantes_ids"],
    })
    assert factura.status_code == 200, factura.text
    factura = factura.json()
    factura = factura.get("factura", factura)
    assert factura.get("cae"), "la factura tiene que haberse emitido de verdad"

    # 4. Los dos pendientes quedaron cerrados y apuntan a esa factura.
    bandeja = admin_client.get(BANDEJA).json()
    assert bandeja["total_pendientes"] == 0
    assert len(bandeja["facturados"]) == 2
    assert {c["factura_id"] for c in bandeja["facturados"]} == {factura["id"]}
    assert {c["resuelto_por"] for c in bandeja["facturados"]} == {"Administrador"}


def test_emitir_sin_ids_no_toca_la_bandeja(admin_client, monkeypatch):
    """Una factura normal, cargada a mano, no cierra nada de la bandeja."""
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    _depositar(admin_client)

    admin_client.post("/api/facturas", json={
        "tipo": 11, "fecha": HOY, "client_name": "Otro", "condicion_venta": "Contado",
        "items": [{"description": "Otra cosa", "qty": 1, "unit_price": 100.0}],
    })

    assert admin_client.get(BANDEJA).json()["total_pendientes"] == 1


def test_un_id_que_no_existe_no_impide_emitir(admin_client, monkeypatch):
    """Para cuando se marca, la factura ya tiene CAE: un id podrido no puede
    hacer fallar la request, o el usuario creería que no se emitió y la
    volvería a cargar."""
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    r = admin_client.post("/api/facturas", json={
        "tipo": 11, "fecha": HOY, "client_name": "Consumidor Final",
        "condicion_venta": "Contado",
        "items": [{"description": "Servicio", "qty": 1, "unit_price": 100.0}],
        "comprobantes_pendientes_ids": [99999],
    })
    assert r.status_code == 200


def test_descartar_lo_saca_de_pendientes(admin_client, monkeypatch):
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    comprobante_id = _depositar(admin_client).json()["id"]

    r = admin_client.post(f"{BANDEJA}/{comprobante_id}/descartar",
                          json={"motivo": "se cobró por fuera"})
    assert r.status_code == 200
    assert r.json()["estado"] == "descartado"

    bandeja = admin_client.get(BANDEJA).json()
    assert bandeja["total_pendientes"] == 0
    assert bandeja["descartados"][0]["motivo_descarte"] == "se cobró por fuera"


def test_reenviar_algo_ya_descartado_da_409(admin_client, monkeypatch):
    """Lo que le permite a LibraDesk dejar de insistir con algo que acá ya se
    resolvió."""
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    comprobante_id = _depositar(admin_client).json()["id"]
    admin_client.post(f"{BANDEJA}/{comprobante_id}/descartar", json={"motivo": ""})

    assert _depositar(admin_client).status_code == 409
