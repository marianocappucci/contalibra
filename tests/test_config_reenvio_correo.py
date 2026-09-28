"""Correo de reenvío (piloto): destino externo al que un proceso central,
fuera de este repo, reenvía lo que llega a la casilla de la instancia
(`<slug>@contalibra.com.ar`).

Mismo `smtp_router` y misma protección que `/api/config/smtp` (ver
`test_config_smtp.py`), montado con `require_admin_o_servicio_json`: admin de
la instancia o token de servicio, éste último para que el proceso central lo
lea sin ser un usuario de la instancia.
"""


def test_sin_sesion_no_se_puede_leer(client):
    assert client.get("/api/config/reenvio-correo").status_code in (401, 403)


def test_operador_no_puede_leer(admin_client):
    """403 y no 401: hay sesión, pero no es admin ni token de servicio."""
    alta = admin_client.post("/api/usuarios", json={
        "username": "operador-reenvio", "name": "O", "password": "clave-123456",
        "role": "operador"})
    assert alta.status_code == 201, alta.text
    admin_client.post("/api/logout")
    login = admin_client.post(
        "/api/login", json={"username": "operador-reenvio", "password": "clave-123456"})
    assert login.status_code == 200, login.text
    assert admin_client.get("/api/config/reenvio-correo").status_code == 403


def test_admin_lee_el_estado_inicial(admin_client):
    r = admin_client.get("/api/config/reenvio-correo")
    assert r.status_code == 200
    assert r.json() == {"destino": None}


def test_admin_guarda_y_lee(admin_client):
    r = admin_client.put("/api/config/reenvio-correo", json={"destino": "cliente@gmail.com"})
    assert r.status_code == 200, r.text
    assert r.json() == {"destino": "cliente@gmail.com"}

    lectura = admin_client.get("/api/config/reenvio-correo")
    assert lectura.json() == {"destino": "cliente@gmail.com"}


def test_destino_null_borra_el_reenvio(admin_client):
    admin_client.put("/api/config/reenvio-correo", json={"destino": "cliente@gmail.com"})
    r = admin_client.put("/api/config/reenvio-correo", json={"destino": None})
    assert r.status_code == 200, r.text
    assert r.json() == {"destino": None}


def test_destino_omitido_tambien_borra_el_reenvio(admin_client):
    """`destino` tiene default `None`: omitirlo es la misma intención que
    mandarlo explícito en `null` — a diferencia de SMTP, acá no hay un
    secreto que "no tocar el campo" tenga que preservar."""
    admin_client.put("/api/config/reenvio-correo", json={"destino": "cliente@gmail.com"})
    r = admin_client.put("/api/config/reenvio-correo", json={})
    assert r.status_code == 200, r.text
    assert r.json() == {"destino": None}


def test_email_invalido_da_422(admin_client):
    r = admin_client.put("/api/config/reenvio-correo", json={"destino": "no-es-un-email"})
    assert r.status_code == 422


def test_el_token_de_servicio_puede_leer_y_escribir(client, monkeypatch):
    """El proceso central de reenvío lo consume por token, no por sesión."""
    monkeypatch.setenv("LIBRA_SERVICE_TOKEN", "token-de-prueba")
    headers = {"x-internal-auth": "token-de-prueba"}

    r = client.put(
        "/api/config/reenvio-correo", json={"destino": "cliente@gmail.com"}, headers=headers,
    )
    assert r.status_code == 200, r.text

    lectura = client.get("/api/config/reenvio-correo", headers=headers)
    assert lectura.json() == {"destino": "cliente@gmail.com"}
