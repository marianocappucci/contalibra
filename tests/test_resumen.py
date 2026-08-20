"""`GET /api/resumen`: los números de una sucursal para el panel del dueño.

Fase 0 del plan de `wiki/analyses/panel-del-dueno-multisucursal.md`. Se prueba
entero contra una sola instancia, sin panel construido.

Lo que más importa acá no es que los números salgan, sino **de qué puerta
entran**: la credencial del panel es distinta del token de servicio a propósito,
porque el token de servicio es por producto y lo comparten instancias de
clientes distintos.
"""
import datetime

import pytest

from libraauth.session_auth import PANEL_TOKEN_ENV

HOY = datetime.date.today().isoformat()
TOKEN = "token-de-panel-para-la-suite"


@pytest.fixture
def con_token_de_panel(monkeypatch):
    monkeypatch.setenv(PANEL_TOKEN_ENV, TOKEN)
    return {"X-Panel-Auth": TOKEN}


def _venta(client, total=3000.0):
    resp = client.post("/api/ventas", json={
        "fecha": HOY,
        "items": [{"nombre": "Gaseosa 500ml", "qty": 2, "precio": total / 2}],
        "pagos": [{"medio": "efectivo", "monto": total}],
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── La puerta ───────────────────────────────────────────────────────────────

def test_sin_credencial_no_entra(client):
    assert client.get("/api/resumen").status_code == 401


def test_con_la_credencial_del_panel_entra(client, con_token_de_panel):
    resp = client.get("/api/resumen", headers=con_token_de_panel)
    assert resp.status_code == 200, resp.text


def test_una_credencial_equivocada_no_entra(client, con_token_de_panel):
    resp = client.get("/api/resumen", headers={"X-Panel-Auth": "otra-cosa"})
    assert resp.status_code == 401


def test_el_token_de_servicio_NO_sirve_para_el_resumen(client, monkeypatch):
    """🔴 El control que justifica la credencial aparte.

    `LIBRA_SERVICE_TOKEN` es por producto: `libradesk-lagrace` y
    `libradesk-compulibra` —dos clientes— comparten uno. Si el resumen lo
    aceptara, la credencial del panel de un cliente abriría las instancias de
    los demás.
    """
    monkeypatch.setenv("LIBRA_SERVICE_TOKEN", "token-de-servicio")
    resp = client.get("/api/resumen", headers={"X-Internal-Auth": "token-de-servicio"})
    assert resp.status_code == 401


def test_un_admin_de_la_instancia_tambien_entra(admin_client):
    """Para que la pantalla del propio producto pueda consumirlo sin duplicarlo."""
    assert admin_client.get("/api/resumen").status_code == 200


# ── Los números ─────────────────────────────────────────────────────────────

def test_una_venta_aparece_en_el_resumen(admin_client):
    antes = admin_client.get("/api/resumen").json()["comercio"]["ventas"]
    _venta(admin_client, total=3000.0)
    despues = admin_client.get("/api/resumen").json()["comercio"]["ventas"]

    assert despues["cantidad"] == antes["cantidad"] + 1
    assert despues["monto"] == antes["monto"] + 3000.0


def test_una_venta_anulada_no_cuenta(admin_client):
    venta = _venta(admin_client)
    con_venta = admin_client.get("/api/resumen").json()["comercio"]["ventas"]["cantidad"]

    admin_client.post(f"/api/ventas/{venta['id']}/anular")

    assert admin_client.get("/api/resumen").json()["comercio"]["ventas"]["cantidad"] == con_venta - 1


def test_sin_cobrar_es_un_conteo_y_no_una_muestra(admin_client):
    """🔴 El motivo de que este módulo exista.

    `get_dashboard_data` devuelve `facturas_sin_cobrar` con `LIMIT 8`. Sumando
    cinco sucursales, "40" sería el tope y no el dato. Con **nueve** facturas
    impagas el conteo tiene que decir 9.
    """
    cliente = admin_client.post("/api/clientes", json={
        "name": "Cliente con cuenta", "cuit_dni": "20111111112",
        "iva_condition": "Consumidor Final",
    }).json()

    # Se cobran a cuenta corriente: así quedan impagas por diseño, sin tener que
    # deshacer nada. La cuenta corriente no es un cobro — `get_cobros_factura`
    # la excluye — que es justo el caso que el cliente pidió poder usar.
    for _ in range(9):
        resp = admin_client.post("/api/ventas", json={
            "fecha": HOY,
            "items": [{"nombre": "Alfajor", "qty": 1, "precio": 100.0}],
            "pagos": [{"medio": "cuenta_corriente", "monto": 100.0}],
            "cliente_id": cliente["id"],
        })
        assert resp.status_code == 200, resp.text
        admin_client.post(f"/api/ventas/{resp.json()['id']}/facturar")

    assert admin_client.get("/api/resumen").json()["nucleo"]["sin_cobrar"]["cantidad"] == 9


def test_la_instancia_se_identifica(admin_client):
    """El panel necesita el CUIT para agrupar por razón social."""
    instancia = admin_client.get("/api/resumen").json()["instancia"]
    assert set(instancia) == {"nombre", "cuit", "punto_venta"}


# ── El período ──────────────────────────────────────────────────────────────

def test_por_defecto_es_el_mes_en_curso(admin_client):
    periodo = admin_client.get("/api/resumen").json()["periodo"]
    hoy = datetime.date.today()
    assert periodo["desde"] == hoy.replace(day=1).isoformat()
    assert periodo["hasta"] == hoy.isoformat()


def test_un_periodo_viejo_no_trae_las_ventas_de_hoy(admin_client):
    _venta(admin_client)
    resp = admin_client.get("/api/resumen", params={"desde": "2020-01-01", "hasta": "2020-01-31"})
    assert resp.json()["comercio"]["ventas"]["cantidad"] == 0


def test_una_fecha_que_no_es_fecha_da_422(admin_client):
    resp = admin_client.get("/api/resumen", params={"desde": "01/08/2026"})
    assert resp.status_code == 422


def test_desde_posterior_a_hasta_da_422(admin_client):
    resp = admin_client.get("/api/resumen", params={"desde": "2026-08-31", "hasta": "2026-08-01"})
    assert resp.status_code == 422
