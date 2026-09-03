"""Slice 4 del paquete mayorista: quiebres por cantidad.

Una lista puede definir, por producto, precios por quiebre de cantidad (ej. 10+ a
$80, 50+ a $70) además del precio base "1+". El motor ya resuelve por cantidad
(`resolve_price`); acá se los guarda/lee y se los expone gateados por `mayorista`.

Corre contra PostgreSQL (fixture `client`/`admin_client`).
"""
from app import database as db


def _habilitar_mayorista():
    with db.get_connection() as conn:
        conn.execute("UPDATE modulos SET habilitado=1 WHERE modulo=?", ("mayorista",))


def _lista_con_producto(base_lista: float = 90.0, base_venta: float = 100.0):
    pid = db.create_producto("Fideos x500g", precio_venta=base_venta)
    lid = db.create_lista_precio("Mayorista")
    db.save_lista_precio_items(lid, {pid: base_lista})  # el precio base "1+"
    return lid, pid


def test_resuelve_el_precio_segun_la_cantidad(client):
    lid, pid = _lista_con_producto()
    db.set_quiebres(lid, pid, [{"min_quantity": 10, "amount": 80}, {"min_quantity": 50, "amount": 70}])
    # Debajo del primer quiebre: precio base.
    assert db.resolver_precio_por_cantidad(lid, pid, 1) == 90
    assert db.resolver_precio_por_cantidad(lid, pid, 9) == 90
    # En y por encima de cada quiebre: el más alto aplicable.
    assert db.resolver_precio_por_cantidad(lid, pid, 10) == 80
    assert db.resolver_precio_por_cantidad(lid, pid, 49) == 80
    assert db.resolver_precio_por_cantidad(lid, pid, 50) == 70
    assert db.resolver_precio_por_cantidad(lid, pid, 500) == 70


def test_set_quiebres_reemplaza_y_no_toca_el_precio_base(client):
    lid, pid = _lista_con_producto()
    db.set_quiebres(lid, pid, [{"min_quantity": 10, "amount": 80}])
    assert db.get_quiebres(lid, pid) == [{"min_quantity": 10.0, "amount": 80.0}]
    # Reemplaza, no acumula.
    db.set_quiebres(lid, pid, [{"min_quantity": 20, "amount": 75}])
    assert db.get_quiebres(lid, pid) == [{"min_quantity": 20.0, "amount": 75.0}]
    # El precio base (fila min_quantity NULL) sigue intacto.
    assert db.get_precio_en_lista(lid, pid) == 90


def test_los_endpoints_dan_403_sin_el_addon(admin_client):
    lid, pid = _lista_con_producto()
    assert admin_client.get(f"/api/listas-precio/{lid}/items/{pid}/quiebres").status_code == 403
    assert admin_client.put(
        f"/api/listas-precio/{lid}/items/{pid}/quiebres", json={"quiebres": []}
    ).status_code == 403
    assert admin_client.get(
        f"/api/listas-precio/{lid}/precio?producto_id={pid}&cantidad=10"
    ).status_code == 403


def test_guardar_leer_y_resolver_por_la_api(admin_client):
    _habilitar_mayorista()
    lid, pid = _lista_con_producto()

    r = admin_client.put(
        f"/api/listas-precio/{lid}/items/{pid}/quiebres",
        json={"quiebres": [{"min_quantity": 10, "amount": 80}]},
    )
    assert r.status_code == 200
    assert r.json() == [{"min_quantity": 10.0, "amount": 80.0}]

    # El presupuesto re-cotiza por acá: base para poca cantidad, quiebre para mucha.
    assert admin_client.get(
        f"/api/listas-precio/{lid}/precio?producto_id={pid}&cantidad=5"
    ).json() == {"precio": 90.0}
    assert admin_client.get(
        f"/api/listas-precio/{lid}/precio?producto_id={pid}&cantidad=10"
    ).json() == {"precio": 80.0}


def test_valida_los_quiebres(admin_client):
    _habilitar_mayorista()
    lid, pid = _lista_con_producto()

    def put(quiebres):
        return admin_client.put(
            f"/api/listas-precio/{lid}/items/{pid}/quiebres", json={"quiebres": quiebres}
        )

    assert put([{"min_quantity": 1, "amount": 80}]).status_code == 422  # cantidad < 2
    assert put([{"min_quantity": 10, "amount": 0}]).status_code == 422  # precio <= 0
    assert put([  # dos quiebres con la misma cantidad
        {"min_quantity": 10, "amount": 80}, {"min_quantity": 10, "amount": 70},
    ]).status_code == 422
    # Ninguno de los rechazos dejó algo guardado.
    assert db.get_quiebres(lid, pid) == []
