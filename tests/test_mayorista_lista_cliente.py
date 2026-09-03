"""El add-on mayorista: asignar una lista de precios a un cliente.

Slice 2 del paquete mayorista (ver wiki/analyses/distribuidora-mayorista-producto-candidato).
Corre contra PostgreSQL (fixture `client`/`admin_client`).

El módulo `mayorista` arranca **apagado** (slice 1), así que por defecto los
endpoints dan 403; se habilitan por instancia. Cada test que necesita el add-on
lo prende explícitamente.
"""
from app import database as db
from app import db_mayorista


def _habilitar_mayorista():
    with db.get_connection() as conn:
        conn.execute("UPDATE modulos SET habilitado=1 WHERE modulo=?", ("mayorista",))


def test_los_endpoints_dan_403_con_el_addon_apagado(admin_client):
    cid = db.create_client("Distribuidora Test")
    # Por defecto `mayorista` está en 0 (seed de slice 1): el gate corta.
    assert admin_client.get(f"/api/clientes/{cid}/lista-precio").status_code == 403
    assert admin_client.put(
        f"/api/clientes/{cid}/lista-precio", json={"lista_id": None}
    ).status_code == 403


def test_asignar_leer_y_limpiar_la_lista_del_cliente(admin_client):
    _habilitar_mayorista()
    cid = db.create_client("Distribuidora Mayorista")
    lid = db.create_lista_precio("Mayorista", "precios por volumen")

    # Arranca sin lista.
    r = admin_client.get(f"/api/clientes/{cid}/lista-precio")
    assert r.status_code == 200
    assert r.json() == {"lista_id": None, "lista": None}

    # Se le asigna.
    r = admin_client.put(f"/api/clientes/{cid}/lista-precio", json={"lista_id": lid})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["lista_id"] == lid
    assert cuerpo["lista"]["id"] == lid and cuerpo["lista"]["nombre"] == "Mayorista"

    # Y se lee de vuelta.
    assert admin_client.get(f"/api/clientes/{cid}/lista-precio").json()["lista_id"] == lid

    # Se limpia (vuelve al precio base).
    r = admin_client.put(f"/api/clientes/{cid}/lista-precio", json={"lista_id": None})
    assert r.status_code == 200
    assert admin_client.get(f"/api/clientes/{cid}/lista-precio").json() == {
        "lista_id": None, "lista": None,
    }


def test_reasignar_pisa_la_lista_anterior(admin_client):
    _habilitar_mayorista()
    cid = db.create_client("Distribuidora")
    l1 = db.create_lista_precio("Lista 1")
    l2 = db.create_lista_precio("Lista 2")

    admin_client.put(f"/api/clientes/{cid}/lista-precio", json={"lista_id": l1})
    admin_client.put(f"/api/clientes/{cid}/lista-precio", json={"lista_id": l2})
    # Una sola fila por cliente (PK): la segunda pisa a la primera.
    assert db_mayorista.get_lista_de_cliente(cid) == l2


def test_asignar_una_lista_inexistente_da_422(admin_client):
    _habilitar_mayorista()
    cid = db.create_client("Distribuidora")
    r = admin_client.put(f"/api/clientes/{cid}/lista-precio", json={"lista_id": 999999})
    assert r.status_code == 422
    # Y no dejó nada asignado.
    assert db_mayorista.get_lista_de_cliente(cid) is None


def test_un_cliente_inexistente_da_404(admin_client):
    _habilitar_mayorista()
    assert admin_client.get("/api/clientes/999999/lista-precio").status_code == 404
    assert admin_client.put(
        "/api/clientes/999999/lista-precio", json={"lista_id": None}
    ).status_code == 404


def test_borrar_la_lista_se_lleva_la_asignacion(client):
    """ON DELETE CASCADE hacia `price_lists`: si se borra la lista, la
    asignación no queda colgada apuntando a una lista que ya no existe."""
    _habilitar_mayorista()
    cid = db.create_client("Distribuidora")
    lid = db.create_lista_precio("Se va a borrar")
    db_mayorista.set_lista_de_cliente(cid, lid)
    assert db_mayorista.get_lista_de_cliente(cid) == lid

    db.delete_lista_precio(lid)
    assert db_mayorista.get_lista_de_cliente(cid) is None
