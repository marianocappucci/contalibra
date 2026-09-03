"""El add-on `mayorista` sobrevive a los cambios de plan.

El paquete mayorista es un add-on pago, fuera de los tres planes (ver
wiki/analyses/distribuidora-mayorista-producto-candidato). `apply_plan` recorre
las filas de `modulos` y apaga lo que el plan no incluye; sin el skip de
`plans.ADDONS` en el motor, subir o bajar de plan lo apagaría — un adicional que
se desactiva solo. Estos tests fijan que no pasa.

Los dos primeros corren contra PostgreSQL (vía la fixture `client`, que arma una
instancia real con el seed de `_MODULOS_DEFAULT`). El tercero es la invariante de
`plans.py` que hace que aplicar un plan nunca alcance a un add-on.
"""
import plans
from app import database as db


def test_mayorista_arranca_apagado_y_fuera_de_todo_plan(client):
    # El seed lo crea (existe la fila) y arranca apagado: es un add-on pago que
    # se habilita después, por instancia.
    assert db.get_modulos()["mayorista"] is False
    for p in plans.PLANES:
        assert "mayorista" not in plans.modulos_de_plan(p)


def test_mayorista_habilitado_sobrevive_a_cada_cambio_de_plan(client):
    # Lo habilita el backoffice para esta instancia.
    with db.get_connection() as conn:
        conn.execute("UPDATE modulos SET habilitado=1 WHERE modulo=?", ("mayorista",))
    assert db.get_modulos()["mayorista"] is True

    for plan in ("basico", "estandar", "premium", "estandar", "basico"):
        db.apply_plan(plan)
        mods = db.get_modulos()
        assert mods["mayorista"] is True, f"el add-on se apagó al aplicar {plan!r}"
        # Control: apply_plan SÍ sigue gateando lo que es de un plan. Sin esto,
        # el assert de arriba pasaría con una función que no hace nada.
        assert mods["stock"] is (plan == "premium")


def test_addons_es_disjunto_de_los_planes():
    """La invariante que hace que aplicar un plan nunca toque un add-on: los
    add-ons no están en ningún plan ni en TODOS_LOS_MODULOS."""
    assert plans.ADDONS.isdisjoint(plans.TODOS_LOS_MODULOS)
    for p in plans.PLANES:
        assert plans.ADDONS.isdisjoint(plans.modulos_de_plan(p))
