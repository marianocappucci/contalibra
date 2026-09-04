"""El remito valorizado de Contalibra: se elige al convertir un presupuesto.

valorizado=True → el remito hereda los precios del presupuesto (los guarda y el
PDF los muestra). valorizado=False (default) → nota de entrega pelada: sin
precios, total 0, ítems sólo con descripción y cantidad.
"""
from app import database as db


def _crear_presupuesto(admin_client):
    resp = admin_client.post("/api/presupuestos", json={
        "date": "2026-09-04", "client_name": "Distribuidora Test", "tax_rate": 0.21,
        "items": [{"description": "Prod A", "qty": 2, "unit_price": 100.0}],
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_convertir_valorizado_hereda_los_precios(admin_client):
    pid = _crear_presupuesto(admin_client)
    resp = admin_client.post(
        f"/api/presupuestos/{pid}/estado",
        json={"estado": "aceptado", "convertir_remito": True, "valorizado": True},
    )
    assert resp.status_code == 200, resp.text
    remito = db.get_remito(db.get_presupuesto(pid)["remito_id"])
    assert remito["total"] == 242.0          # 200 + 21%
    assert remito["items"][0]["unit_price"] == 100.0
    assert remito["items"][0]["subtotal"] == 200.0


def test_convertir_pelado_tira_los_precios(admin_client):
    pid = _crear_presupuesto(admin_client)
    resp = admin_client.post(
        f"/api/presupuestos/{pid}/estado",
        json={"estado": "aceptado", "convertir_remito": True, "valorizado": False},
    )
    assert resp.status_code == 200, resp.text
    remito = db.get_remito(db.get_presupuesto(pid)["remito_id"])
    assert remito["total"] == 0
    item = remito["items"][0]
    assert item["description"] == "Prod A"
    assert "unit_price" not in item          # sin precio: nota de entrega pelada
