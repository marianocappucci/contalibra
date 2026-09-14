"""Gestion de usuarios -- desde el 2026-09-13 (ADR-018, libraauth v0.43.0)
el router lo sirve `libraauth.usuarios.build_users_router()`
(`app/web/api/usuarios.py`), no una copia propia.

**Lo que se borro de este archivo, y por que:**

- `test_no_degradar_al_unico_admin`, `test_no_borrar_al_unico_admin_ni_a_
  si_mismo`, `test_borrar_usuario`, `test_cambiar_password_de_otro_via_
  update`: las protecciones que ejercian (unico admin, borrado, reset de la
  contraseña de otro) las prueba `libraauth` UNA SOLA VEZ en su propia
  suite (`tests/test_usuarios_router.py`) y las ejerce igual el ciclo
  completo de `verificar_contrato_de_usuarios` de abajo (alta / edicion /
  releer / resetear password / borrar / 404). Mantenerlas acá además sería
  duplicar exactamente lo que el motor ya prueba -- ver README de
  libraauth, seccion "Adoptarla en un producto", paso 3.
- `test_editar_con_contrato_libraauth_persiste_el_nombre`,
  `test_crear_con_contrato_libraauth`,
  `test_listar_devuelve_las_claves_de_los_dos_contratos`,
  `test_contrato_viejo_nombre_activo_sigue_funcionando`,
  `test_editar_con_contrato_libraauth_no_borra_el_email`: probaban el
  aditivo POR ALIAS (`nombre`/`activo` + `name`/`active` a la vez, PR
  #313/#299) que este cambio REEMPLAZA -- el router nuevo habla un solo
  contrato (`name`/`active`/`email`, `id: str`) y ya no acepta
  `nombre`/`activo`. `test_contrato_viejo_nombre_activo_sigue_funcionando`
  en particular pasaría a estar mal: un PUT con esas claves ahora da 422
  (`name`/`role` son obligatorios y no tienen alias).
- `test_cambiar_mi_password`: probaba `PUT /api/usuarios/me/password`, que
  se elimina (cambiaba la contraseña propia SIN pedir la actual). La
  contraparte es `POST /api/change-password`, que sí la pide -- se prueba
  en `test_cambiar_mi_password_pide_la_actual` más abajo.

**Lo que SÍ se mantiene** (comportamiento propio de Contalibra que
`build_users_router` no prueba por sí solo, porque depende de la tupla de
roles y el guard que este producto le pasa): admin-only, contraseña corta,
rol de OTRO producto rechazado, un usuario desactivado no puede loguear, y
username duplicado -- este último con el código nuevo: **409**, no 422 (ver
tabla de protecciones del ADR-018 -- antes de esta adopción daba 422)."""
from libraauth.testing import verificar_contrato_de_usuarios

from tests.conftest import ADMIN_PASS, ADMIN_USER


def _crear(client, username="operador1", role="operador", password="clave-123456"):
    resp = client.post("/api/usuarios", json={
        "username": username, "name": f"Usuario {username}",
        "email": f"{username}@suite.test", "password": password, "role": role,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_contrato_de_usuarios_libraauth(admin_client):
    """El ciclo completo que ejerce el backoffice -- listar, alta, editar,
    releer por GET /{id}, resetear password, borrar, 404 -- contra ESTA
    instancia del router (con `roles=("admin","operador","cajero")` y el
    guard `require_admin_o_servicio_json` que ya usaba Contalibra).

    `role="operador"`: el default `"staff"` del helper no es un rol válido
    acá (ver `ROLES` en `app/db_usuarios.py`)."""
    verificar_contrato_de_usuarios(admin_client, "/api/usuarios", role="operador")


def test_router_es_admin_only(client):
    _con_admin = client.post("/api/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert _con_admin.status_code == 200
    _crear(client, "operador2", role="operador")
    client.post("/api/logout")
    login = client.post("/api/login", json={"username": "operador2", "password": "clave-123456"})
    assert login.status_code == 200
    assert client.get("/api/usuarios").status_code == 403


def test_crear_y_loguear_usuario_nuevo(admin_client):
    _crear(admin_client, "cajero1", role="cajero")
    admin_client.post("/api/logout")
    login = admin_client.post("/api/login",
                              json={"username": "cajero1", "password": "clave-123456"})
    assert login.status_code == 200
    assert login.json()["role"] == "cajero"


def test_crear_password_corta_422(admin_client):
    resp = admin_client.post("/api/usuarios", json={
        "username": "corto", "name": "X", "password": "123", "role": "cajero"})
    assert resp.status_code == 422


def test_crear_rol_de_otro_producto_422(admin_client):
    """`staff` es el rol default de los otros seis productos de la familia
    -- acá tiene que rechazarse igual que cualquier rol inventado."""
    resp = admin_client.post("/api/usuarios", json={
        "username": "raro", "name": "X", "password": "clave-123456", "role": "staff"})
    assert resp.status_code == 422


def test_crear_username_duplicado_409(admin_client):
    """🔴 Cambio de comportamiento: antes de esta adopción daba 422 (el
    router propio no distinguía username duplicado de cualquier otro
    `ValueError`). `build_users_router` atrapa `UsernameTaken` y responde
    409 -- ver la tabla de protecciones del ADR-018."""
    _crear(admin_client, "repetido")
    resp = admin_client.post("/api/usuarios", json={
        "username": "repetido", "name": "Otro", "password": "clave-123456", "role": "cajero"})
    assert resp.status_code == 409


def test_desactivar_usuario_bloquea_su_login(admin_client):
    creado = _crear(admin_client, "temporal", role="operador")
    resp = admin_client.put(f"/api/usuarios/{creado['id']}", json={
        "name": creado["name"], "role": "operador", "active": False})
    assert resp.status_code == 200
    admin_client.post("/api/logout")
    assert admin_client.post("/api/login", json={
        "username": "temporal", "password": "clave-123456"}).status_code == 401


def test_eliminar_devuelve_204_sin_cuerpo(admin_client):
    """🔴 Cambio de comportamiento: antes de esta adopción `DELETE` devolvía
    `200 {"ok": true}` -- ahora `204` sin cuerpo (ver ADR-018; el frontend
    propio no miraba el cuerpo del borrado, así que no hay nada que
    migrar del lado de la SPA)."""
    creado = _crear(admin_client, "efimero")
    resp = admin_client.delete(f"/api/usuarios/{creado['id']}")
    assert resp.status_code == 204
    assert resp.text == ""


def test_borrar_usuario_con_turno_abierto_409(admin_client):
    """Riesgo detectado el 2026-09-14 (orquestador, revisando la factory):
    `turnos_caja.usuario_id` es NOT NULL REFERENCES usuarios(id) SIN
    'ON DELETE SET NULL' (a diferencia del resto de las FK a usuarios en
    libracore/db/schema.py, todas SET NULL) -- borrar un usuario que abrió
    un turno choca contra esa FK. Hasta libraauth v0.43.0
    `build_users_router().eliminar` sólo atrapaba `KeyError`, y un
    `IntegrityError` de Postgres subía sin atrapar como 500. **v0.43.1 lo
    arregla**: atrapa la violación de FK, hace rollback de la sesión y
    responde 409 -- ver el pin en `pyproject.toml`."""
    creado = _crear(admin_client, "cajero-con-turno", role="cajero")
    admin_client.post("/api/logout")
    login = admin_client.post("/api/login", json={
        "username": "cajero-con-turno", "password": "clave-123456"})
    assert login.status_code == 200
    abierto = admin_client.post("/api/turnos/abrir", json={"monto_inicial": 1000.0})
    assert abierto.status_code == 200, abierto.text
    admin_client.post("/api/logout")
    admin_client.post("/api/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})

    resp = admin_client.delete(f"/api/usuarios/{creado['id']}")
    assert resp.status_code == 409, resp.text


def test_cambiar_mi_password_pide_la_actual(admin_client):
    """Reemplaza a `PUT /api/usuarios/me/password` (eliminado): la propia
    contraseña se cambia con `POST /api/change-password`
    (`build_json_api_auth_router(prefix="/api")`, montado en
    `app/web/api/auth.py`), que sí exige la actual."""
    # La actual equivocada no cambia nada -- 400, no 401: la sesión sigue
    # siendo válida, lo que está mal es el dato del formulario.
    mal = admin_client.post("/api/change-password", json={
        "current_password": "no-es-esta", "new_password": "otra-clave-77"})
    assert mal.status_code == 400, mal.text

    resp = admin_client.post("/api/change-password", json={
        "current_password": ADMIN_PASS, "new_password": "otra-clave-77"})
    assert resp.status_code == 200, resp.text

    admin_client.post("/api/logout")
    assert admin_client.post("/api/login", json={
        "username": ADMIN_USER, "password": ADMIN_PASS}).status_code == 401
    assert admin_client.post("/api/login", json={
        "username": ADMIN_USER, "password": "otra-clave-77"}).status_code == 200


def test_me_password_ya_no_es_un_endpoint_propio(admin_client):
    """El endpoint viejo (`PUT /api/usuarios/me/password`, sin pedir la
    actual) se borró. La ruta sigue "existiendo" en un sentido sintáctico
    -- coincide con `PUT /api/usuarios/{user_id}/password` de
    `build_users_router`, tratando el literal `"me"` como un ID de usuario
    -- pero eso es justo la prueba de que no hay ninguna interpretación
    mágica de "me" como "el usuario de la sesión": con el campo correcto
    del contrato nuevo (`password`, no `new_password`) da **404**, porque
    ningún usuario tiene el id `"me"`. El viejo cuerpo (`new_password`)
    directamente ni valida (422, campo faltante)."""
    viejo = admin_client.put("/api/usuarios/me/password", json={"new_password": "x" * 6})
    assert viejo.status_code == 422, viejo.text

    resp = admin_client.put("/api/usuarios/me/password", json={"password": "x" * 6})
    assert resp.status_code == 404, resp.text
