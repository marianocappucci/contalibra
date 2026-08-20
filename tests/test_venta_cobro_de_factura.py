"""La factura de una venta ya cobrada no puede figurar "Sin cobrar".

Reportado el 2026-08-20 mirando Comprobantes en producción: 8 facturas de ventas
pagadas por QR contadas como pendientes. Una factura figura cobrada cuando hay
`caja_movimientos` con su `factura_id`; los de una venta se crean **antes** de
que la factura exista y sin ese campo.

🔴 El arreglo **vincula** el movimiento que ya está, no registra uno nuevo:
pasar por `registrar_cobro_factura` habría contado el mismo dinero dos veces.
Por eso cada test de acá mira la caja entera además del estado del comprobante.
"""
import datetime

from app import database as db

HOY = datetime.date.today().isoformat()


def _venta(client, pagos=None, **extra):
    payload = {
        "fecha": HOY,
        "items": [{"nombre": "Gaseosa 500ml", "qty": 2, "precio": 1500.0}],
        "pagos": pagos or [{"medio": "efectivo", "monto": 3000.0}],
    }
    payload.update(extra)
    resp = client.post("/api/ventas", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _caja():
    movimientos = db.get_caja_movimientos()
    return len(movimientos), round(sum(float(m["monto"]) for m in movimientos), 2)


def test_la_factura_de_una_venta_queda_cobrada(admin_client):
    venta = _venta(admin_client)
    factura = admin_client.post(f"/api/ventas/{venta['id']}/facturar").json()["factura"]

    detalle = admin_client.get(f"/api/facturas/{factura['id']}").json()

    assert detalle["total_cobrado"] == venta["total"]
    assert detalle["pendiente"] == 0.0


def test_vincular_el_cobro_no_agrega_plata_a_la_caja(admin_client):
    """El control que importa: la caja tiene que quedar exactamente igual."""
    venta = _venta(admin_client)
    antes = _caja()
    assert antes == (1, venta["total"]), "la venta deja un movimiento por su cobro"

    admin_client.post(f"/api/ventas/{venta['id']}/facturar")

    assert _caja() == antes


def test_un_pago_dividido_cubre_la_factura_entera(admin_client):
    venta = _venta(admin_client, pagos=[
        {"medio": "efectivo", "monto": 1000.0},
        {"medio": "mercadopago", "monto": 2000.0},
    ])
    factura = admin_client.post(f"/api/ventas/{venta['id']}/facturar").json()["factura"]

    detalle = admin_client.get(f"/api/facturas/{factura['id']}").json()

    assert detalle["total_cobrado"] == 3000.0
    assert detalle["pendiente"] == 0.0
    assert len(detalle["cobros"]) == 2


def test_no_se_lleva_puestos_los_movimientos_de_otra_venta(admin_client):
    """El vínculo es por número de venta: la de al lado no se toca."""
    otra = _venta(admin_client)
    venta = _venta(admin_client)

    factura = admin_client.post(f"/api/ventas/{venta['id']}/facturar").json()["factura"]

    cobros = admin_client.get(f"/api/facturas/{factura['id']}").json()["cobros"]
    assert len(cobros) == 1
    assert venta["numero"] in cobros[0]["concepto"]
    assert otra["numero"] not in cobros[0]["concepto"]


def test_una_venta_en_cuenta_corriente_deja_la_factura_pendiente(admin_client):
    """El caso que el cliente pidió: dejar la factura impaga a propósito.

    La cuenta corriente no es un cobro — `get_cobros_factura` la excluye — así
    que la factura tiene que seguir figurando pendiente.
    """
    cliente = admin_client.post("/api/clientes", json={
        "name": "Cliente con cuenta", "cuit_dni": "20111111112",
        "iva_condition": "Consumidor Final",
    }).json()
    venta = _venta(admin_client, cliente_id=cliente["id"],
                   pagos=[{"medio": "cuenta_corriente", "monto": 3000.0}])
    factura = admin_client.post(f"/api/ventas/{venta['id']}/facturar").json()["factura"]

    detalle = admin_client.get(f"/api/facturas/{factura['id']}").json()

    assert detalle["total_cobrado"] == 0.0
    assert detalle["pendiente"] == 3000.0
