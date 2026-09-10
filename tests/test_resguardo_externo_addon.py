"""El enlace de la copia externa es un ADD-ON: apagado hasta que se paga.

`resguardo_externo` no pertenece a ningún plan (ver `plans.ADDONS`): viene
apagado y lo prende el backoffice por instancia, con `db.set_addon` por
`docker exec`. El router del motor (`libracore.resguardo_enlace`) se monta en
`app/web/app.py` detrás de dos gates —admin y el del módulo—, y libra-ui trata
el 403 como "sin plan".

Lo que fijan, en orden de lo que se pierde sin que se note:

1. Que sin el add-on la ruta **no responde**, ni con la fila apagada ni sin
   fila. Un gate que se cae deja a cualquier admin conectar su nube gratis.
2. Que prenderlo con el mecanismo real del backoffice la **abre**. Es el
   control del punto 1: sin él, un 403 permanente (una ruta mal montada) lo
   dejaría en verde.
3. Que el gate de admin sigue ahí aunque el add-on esté prendido.
4. Que aplicar un plan —subir o bajar— no lo apaga, que es lo que se paga.
"""
import plans
from app import database as db
from app import db_core
from tests.conftest import ADMIN_PASS, ADMIN_USER

RUTA = "/api/config/resguardo-externo/enlace"


def _crear_operador(admin_client, username="operador1", password="clave-123456"):
    r = admin_client.post("/api/usuarios", json={
        "username": username, "nombre": f"Usuario {username}",
        "email": f"{username}@suite.test", "password": password, "role": "operador",
    })
    assert r.status_code == 200, r.text


# ── apagado por defecto ──────────────────────────────────────────────────────

def test_el_seed_lo_crea_apagado(client):
    """La fila existe desde el arranque y está en 0: el backoffice la
    encuentra, y nadie la tiene prendida sin haberla pagado."""
    assert db.get_modulos()["resguardo_externo"] is False


def test_con_el_addon_apagado_el_admin_recibe_403(admin_client):
    assert db.get_modulos()["resguardo_externo"] is False

    r = admin_client.get(RUTA)

    assert r.status_code == 403, r.text
    assert "resguardo_externo" in r.json()["detail"]


def test_sin_fila_en_modulos_tambien_da_403(admin_client):
    """Una instancia vieja cuyo seed no la creó todavía: la fila que falta
    cuenta como apagada, no como prendida."""
    with db.get_connection() as conn:
        conn.execute("DELETE FROM modulos WHERE modulo=?", ("resguardo_externo",))
    assert "resguardo_externo" not in db.get_modulos()

    assert admin_client.get(RUTA).status_code == 403


def test_el_403_del_modulo_cubre_tambien_conectar_y_desconectar(admin_client):
    """El gate va en el `include_router`, así que alcanza a todas las rutas del
    router y no sólo al GET."""
    assert admin_client.post(f"{RUTA}/drive").status_code == 403
    assert admin_client.delete(RUTA).status_code == 403


# ── prendido por el backoffice ───────────────────────────────────────────────

def test_prendido_con_set_addon_el_admin_ve_el_estado(admin_client):
    """`db.set_addon` es lo que corre el backoffice por `docker exec`."""
    db.set_addon("resguardo_externo", True)

    r = admin_client.get(RUTA)

    assert r.status_code == 200, r.text
    datos = r.json()
    assert set(datos) >= {"proveedores", "enlace"}, datos
    # Sin enlace hecho todavía: la instancia no está conectada a ninguna nube.
    assert datos["enlace"] is None
    assert isinstance(datos["proveedores"], list)


def test_apagarlo_de_nuevo_vuelve_a_cerrar_la_ruta(admin_client):
    db.set_addon("resguardo_externo", True)
    assert admin_client.get(RUTA).status_code == 200

    db.set_addon("resguardo_externo", False)

    assert admin_client.get(RUTA).status_code == 403


# ── el gate de admin no depende del add-on ───────────────────────────────────

def test_sin_sesion_no_entra(client):
    db.set_addon("resguardo_externo", True)
    assert client.get(RUTA).status_code in (401, 403)


def test_un_usuario_no_admin_no_entra_aunque_el_addon_este_prendido(client):
    """Con el add-on prendido, el 403 que queda sólo puede venir del gate de
    admin — así el test no pasa por el gate equivocado."""
    login = client.post("/api/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert login.status_code == 200
    _crear_operador(client)
    db.set_addon("resguardo_externo", True)
    # Control: el admin sí entra, así que la ruta está abierta por el módulo.
    assert client.get(RUTA).status_code == 200
    client.post("/api/logout")

    login = client.post("/api/login", json={"username": "operador1", "password": "clave-123456"})
    assert login.status_code == 200

    assert client.get(RUTA).status_code in (401, 403)


# ── plans.py y los cambios de plan ───────────────────────────────────────────

def test_es_un_addon_y_no_esta_en_ningun_plan():
    assert "resguardo_externo" in plans.ADDONS
    assert "resguardo_externo" not in plans.TODOS_LOS_MODULOS
    for p in plans.PLANES:
        assert "resguardo_externo" not in plans.modulos_de_plan(p), p


def test_aplicar_un_plan_no_lo_apaga(client):
    """Los dos caminos que aplican un plan: `apply_plan` (motor, dentro de la
    instancia) y `aplicar_plan_en_db` (el del backoffice, sobre la URL)."""
    db.set_addon("resguardo_externo", True)

    for plan in ("basico", "premium", "estandar"):
        db.apply_plan(plan)
        mods = db.get_modulos()
        assert mods["resguardo_externo"] is True, f"apply_plan({plan!r}) lo apagó"
        # Control: el plan SÍ se aplicó. Sin esto, el assert de arriba pasaría
        # con una función que no hace nada.
        assert mods["stock"] is (plan == "premium")

    for plan in ("premium", "basico"):
        plans.aplicar_plan_en_db(db_core.DB_PATH, plan)
        mods = db.get_modulos()
        assert mods["resguardo_externo"] is True, f"aplicar_plan_en_db({plan!r}) lo apagó"
        assert mods["stock"] is (plan == "premium")


def test_aplicar_un_plan_tampoco_lo_prende(client):
    """La otra mitad: subir al plan más alto no regala el add-on."""
    plans.aplicar_plan_en_db(db_core.DB_PATH, "premium")
    assert db.get_modulos()["resguardo_externo"] is False
