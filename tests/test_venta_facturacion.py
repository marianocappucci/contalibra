"""Facturación de una venta — el camino que faltaba (2026-08-19).

Antes de esto `vincular_venta_factura()` no tenía ningún call site: la pestaña
"Facturadas" de Ventas no la podía llenar nada, ni el botón del detalle (un link
al formulario vacío) ni el webhook de MercadoPago, que ante un pago de venta
retornaba antes del bloque de facturación.

Con `ENV=development` (lo fija `conftest.py`) la numeración es local y el CAE
simulado, así que la suite recorre el flujo entero sin tocar ARCA.
"""
import datetime

from app import database as db
from app import mp_api

HOY = datetime.date.today().isoformat()


def _venta(client, items=None, pagos=None, **extra):
    payload = {
        "fecha": HOY,
        "items": items or [{"nombre": "Gaseosa 500ml", "qty": 2, "precio": 1500.0}],
        "pagos": pagos or [{"medio": "efectivo", "monto": 3000.0}],
    }
    payload.update(extra)
    resp = client.post("/api/ventas", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _caja() -> tuple[int, float]:
    """Cuántos movimientos hay y cuánta plata suman.

    A propósito mira la caja ENTERA y no los movimientos de esta venta: si la
    facturación registrara un cobro propio, su concepto sería el de la factura
    ("Cobro Factura C 0001-…") y no nombraría a la venta — un filtro por número
    de venta no lo vería y el test pasaría en verde con el ingreso duplicado.
    """
    movimientos = db.get_caja_movimientos()
    return len(movimientos), round(sum(float(m["monto"]) for m in movimientos), 2)


def test_facturar_una_venta_la_emite_y_la_vincula(admin_client):
    venta = _venta(admin_client)
    resp = admin_client.post(f"/api/ventas/{venta['id']}/facturar")
    assert resp.status_code == 200, resp.text

    factura = resp.json()["factura"]
    assert factura["total"] == venta["total"]
    assert factura["cae"], "la factura tiene que salir con CAE (simulado en dev)"

    detalle = admin_client.get(f"/api/ventas/{venta['id']}").json()
    assert detalle["factura_id"] == factura["id"]


def test_la_venta_facturada_aparece_en_la_solapa(admin_client):
    venta = _venta(admin_client)
    admin_client.post(f"/api/ventas/{venta['id']}/facturar")

    facturadas = admin_client.get("/api/ventas", params={"tab": "facturadas"}).json()
    sin_facturar = admin_client.get("/api/ventas", params={"tab": "sin_facturar"}).json()
    assert any(v["id"] == venta["id"] for v in facturadas)
    assert not any(v["id"] == venta["id"] for v in sin_facturar)


def test_facturar_dos_veces_no_emite_dos_comprobantes(admin_client):
    """Es lo que sostiene el reintento del webhook: MercadoPago puede repetir
    la notificación del mismo pago."""
    venta = _venta(admin_client)
    primera = admin_client.post(f"/api/ventas/{venta['id']}/facturar").json()["factura"]
    segunda = admin_client.post(f"/api/ventas/{venta['id']}/facturar").json()["factura"]

    assert primera["id"] == segunda["id"]
    assert len(admin_client.get("/api/facturas").json()["items"]) == 1


def test_no_se_factura_una_venta_anulada(admin_client):
    venta = _venta(admin_client)
    admin_client.post(f"/api/ventas/{venta['id']}/anular")
    resp = admin_client.post(f"/api/ventas/{venta['id']}/facturar")
    assert resp.status_code == 422
    assert "anulada" in resp.json()["detail"].lower()


def test_venta_inexistente_422(admin_client):
    assert admin_client.post("/api/ventas/99999/facturar").status_code == 422


def test_sin_cliente_se_factura_a_consumidor_final_sin_crearlo(admin_client):
    """La decisión del 2026-08-19: un mostrador con 200 ventas por día no puede
    dejar 200 clientes nuevos en la tabla."""
    antes = len(admin_client.get("/api/clientes").json())
    venta = _venta(admin_client)
    factura = admin_client.post(f"/api/ventas/{venta['id']}/facturar").json()["factura"]

    assert factura["cliente_razon"] == "Consumidor Final"
    assert not factura["cliente_cuit"]
    assert len(admin_client.get("/api/clientes").json()) == antes


def test_con_cliente_asignado_la_factura_sale_a_su_nombre(admin_client):
    cliente = admin_client.post("/api/clientes", json={
        "name": "Complejo Padel SRL", "cuit_dni": "30712345678",
        "iva_condition": "Responsable Inscripto",
    }).json()
    venta = _venta(admin_client, cliente_id=cliente["id"])
    factura = admin_client.post(f"/api/ventas/{venta['id']}/facturar").json()["factura"]

    assert factura["cliente_razon"] == "Complejo Padel SRL"
    assert factura["cliente_cuit"] == "30712345678"


def test_los_items_de_la_venta_van_a_la_factura(admin_client):
    venta = _venta(admin_client, items=[
        {"nombre": "Agua sin gas", "qty": 3, "precio": 1000.0},
        {"nombre": "Alfajor", "qty": 1, "precio": 2000.0},
    ], pagos=[{"medio": "efectivo", "monto": 5000.0}])
    factura = admin_client.post(f"/api/ventas/{venta['id']}/facturar").json()["factura"]

    descripciones = [i["description"] for i in factura["items"]]
    assert descripciones == ["Agua sin gas", "Alfajor"]
    assert factura["total"] == 5000.0


def test_el_descuento_de_la_venta_baja_el_total_de_la_factura(admin_client):
    venta = _venta(admin_client,
                   items=[{"nombre": "Combo", "qty": 1, "precio": 10000.0}],
                   pagos=[{"medio": "efectivo", "monto": 9000.0}],
                   descuento=1000.0)
    factura = admin_client.post(f"/api/ventas/{venta['id']}/facturar").json()["factura"]

    assert factura["total"] == 9000.0 == venta["total"]
    assert any(i["description"] == "Descuento" for i in factura["items"])


def test_facturar_no_vuelve_a_registrar_el_cobro_en_caja(admin_client):
    """La venta ya registró su movimiento al cobrarse. Si la facturación
    agregara otro —como hace `mp_facturacion` para los cobros sueltos— el
    ingreso quedaría contado dos veces."""
    venta = _venta(admin_client)
    antes = _caja()
    assert antes == (1, venta["total"]), "la venta deja un movimiento por su cobro"

    admin_client.post(f"/api/ventas/{venta['id']}/facturar")

    assert _caja() == antes


# ── El webhook: es el caso que el cliente compra ────────────────────────────

def _pago_qr(venta_id: int, monto: float, status: str = "approved") -> dict:
    return {
        "id": 987654321, "status": status, "transaction_amount": monto,
        "external_reference": f"venta-{venta_id}",
        "payer": {"email": "comprador@ejemplo.com"},
        "payment_type_id": "account_money",
    }


def _configurar_mp(client, auto: bool):
    client.put("/api/config/mp", json={
        "mp_access_token": "TEST-token-de-suite",
        "mp_auto_facturar_ventas": auto,
    })


def test_el_qr_acreditado_factura_solo_si_esta_activado(admin_client, monkeypatch):
    venta = _venta(admin_client)
    _configurar_mp(admin_client, auto=True)

    async def _pago(payment_id, access_token):
        return _pago_qr(venta["id"], venta["total"])

    monkeypatch.setattr(mp_api, "obtener_pago", _pago)

    resp = admin_client.post("/webhooks/mercadopago",
                             json={"type": "payment", "data": {"id": "987654321"}})
    assert resp.status_code == 200, resp.text

    detalle = admin_client.get(f"/api/ventas/{venta['id']}").json()
    assert detalle["factura_id"], "el QR acreditado tenía que dejar la venta facturada"


def test_apagado_el_qr_acredita_pero_no_factura(admin_client, monkeypatch):
    """El default. Emitir comprobantes fiscales solo es una decisión del
    cliente, no algo que se prenda por venir de fábrica."""
    venta = _venta(admin_client)
    _configurar_mp(admin_client, auto=False)

    async def _pago(payment_id, access_token):
        return _pago_qr(venta["id"], venta["total"])

    monkeypatch.setattr(mp_api, "obtener_pago", _pago)

    admin_client.post("/webhooks/mercadopago",
                      json={"type": "payment", "data": {"id": "987654322"}})

    detalle = admin_client.get(f"/api/ventas/{venta['id']}").json()
    assert detalle["mp_payment_id"] == "987654322"
    assert not detalle["factura_id"]


def test_un_qr_rechazado_no_factura(admin_client, monkeypatch):
    venta = _venta(admin_client)
    _configurar_mp(admin_client, auto=True)

    async def _pago(payment_id, access_token):
        return _pago_qr(venta["id"], venta["total"], status="rejected")

    monkeypatch.setattr(mp_api, "obtener_pago", _pago)

    admin_client.post("/webhooks/mercadopago",
                      json={"type": "payment", "data": {"id": "987654323"}})

    detalle = admin_client.get(f"/api/ventas/{venta['id']}").json()
    assert not detalle["factura_id"]
