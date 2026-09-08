"""La conversión presupuesto→remito de Contalibra, ahora delegada al motor.

Contalibra ya no reimplementa la conversión: `_convertir_a_remito` enchufa el
generador de PDF del producto (la arista) y delega en libracore v1.79.0
(`convertir_presupuesto_a_remito`). Esto fija que el wiring quede bien: crear el
presupuesto, convertir, y que el remito copie los importes, quede linkeado y
tenga su PDF.
"""
from app import database as db
from app.web.api.presupuestos import _convertir_a_remito

ITEMS = [{"description": "Prod A", "qty": 2, "unit_price": 150.0, "subtotal": 300.0}]


def test_convertir_delega_en_el_motor_copia_importes_y_linkea(client):
    pres_id = db.create_presupuesto(
        number="P-1", date="2026-09-03", valid_until="2026-09-30",
        client_id=None, client_name="Distribuidora Test", client_address="",
        client_cuit="", client_email="", client_phone="",
        items=ITEMS, subtotal=300.0, tax_rate=21.0, tax_amount=63.0, total=363.0,
        observations="entrega lunes",
    )

    _convertir_a_remito(db.get_presupuesto(pres_id), valorizado=True)

    pres = db.get_presupuesto(pres_id)
    assert pres["remito_id"] is not None
    remito = db.get_remito(pres["remito_id"])
    assert remito["items"] == ITEMS
    assert remito["subtotal"] == 300.0
    assert remito["total"] == 363.0
    assert remito["client_name"] == "Distribuidora Test"
    assert remito["observations"] == "entrega lunes"
    # la arista del producto (el PDF de Contalibra) se generó y se guardó
    assert remito["pdf_path"]


# ── El detalle por ítem sobrevive las dos conversiones ───────────────────────
# El remito valorizado copia los ítems verbatim, así que ahí el detalle viaja
# solo. El PELADO no: recorta cada ítem a los campos que quiere conservar, y un
# campo nuevo se cae de esa lista sin que nada falle.

ITEMS_CON_DETALLE = [{
    "description": "Prod A", "qty": 2, "unit_price": 150.0, "subtotal": 300.0,
    "detalle": "presentación por 6, entrega fraccionada",
}]


def _presupuesto_con_detalle():
    return db.create_presupuesto(
        number="P-2", date="2026-09-08", valid_until="2026-10-08",
        client_id=None, client_name="Distribuidora Test", client_address="",
        client_cuit="", client_email="", client_phone="",
        items=ITEMS_CON_DETALLE, subtotal=300.0, tax_rate=21.0, tax_amount=63.0,
        total=363.0, observations="",
    )


def test_el_remito_valorizado_se_lleva_el_detalle(client):
    pres_id = _presupuesto_con_detalle()
    _convertir_a_remito(db.get_presupuesto(pres_id), valorizado=True)
    remito = db.get_remito(db.get_presupuesto(pres_id)["remito_id"])
    assert remito["items"][0]["detalle"] == "presentación por 6, entrega fraccionada"


def test_el_remito_pelado_tira_los_precios_pero_no_el_detalle(client):
    """🔴 Lo pelado es el precio, no la descripción.

    El detalle dice QUÉ se entrega; sacarlo dejaría la nota de entrega diciendo
    menos que el presupuesto que la originó, que es lo que se firma contra la
    mercadería.
    """
    pres_id = _presupuesto_con_detalle()
    _convertir_a_remito(db.get_presupuesto(pres_id), valorizado=False)
    remito = db.get_remito(db.get_presupuesto(pres_id)["remito_id"])

    item = remito["items"][0]
    assert item["detalle"] == "presentación por 6, entrega fraccionada"
    assert item["description"] == "Prod A"
    # y sigue pelado de precios, que es lo que la opción promete
    assert "unit_price" not in item and "subtotal" not in item
    assert remito["total"] == 0


def test_el_pelado_no_inventa_la_clave_cuando_no_hay_detalle(client):
    """Control: sin detalle, el ítem del remito queda como siempre."""
    pres_id = db.create_presupuesto(
        number="P-3", date="2026-09-08", valid_until="2026-10-08",
        client_id=None, client_name="Distribuidora Test", client_address="",
        client_cuit="", client_email="", client_phone="",
        items=ITEMS, subtotal=300.0, tax_rate=21.0, tax_amount=63.0, total=363.0,
        observations="",
    )
    _convertir_a_remito(db.get_presupuesto(pres_id), valorizado=False)
    remito = db.get_remito(db.get_presupuesto(pres_id)["remito_id"])
    assert remito["items"][0] == {"description": "Prod A", "qty": 2}
