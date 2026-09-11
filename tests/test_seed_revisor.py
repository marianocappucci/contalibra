"""El revisor de integraciones y la copia externa en la demo.

El reset diario borra la base, así que lo que el revisor de Dropbox necesita
para probar la copia externa —un usuario admin y el add-on prendido— tiene que
volver a nacer con el seed. Lo que fijan estos tests:

1. 🔴 **Sin credenciales en el entorno, no hay revisor.** La clave no puede
   vivir en el repo, que es público: si el entorno no la trae, el seed no
   inventa una.
2. **Con credenciales, el revisor es admin**, y correr el seed dos veces no lo
   duplica y le vuelve a fijar la clave.
3. 🔴 **El add-on sólo se toca en una demo** (`DEMO_MODE=1`).
"""
import json

import pytest
from fastapi.testclient import TestClient

from app import database as db
from app.web.app import app
from scripts.seed_demo import (
    ADDON_COPIA_EXTERNA,
    ENV_REVISOR_PASSWORD,
    ENV_REVISOR_USUARIO,
    Api,
    _lista,
    _prender_copia_externa,
    _sembrar_revisor,
    sembrar,
)


class _ApiDeTest(Api):
    """Mismo doble que `test_seed_demo.py`: habla con el `TestClient`."""

    def __init__(self, client):
        self.client = client

    def _pedir(self, metodo, ruta, cuerpo=None):
        datos = json.dumps(cuerpo, default=str) if cuerpo is not None else None
        respuesta = self.client.request(
            metodo, ruta, content=datos,
            headers={"Content-Type": "application/json"} if datos else None,
        )
        if respuesta.status_code >= 400:
            raise RuntimeError(f"{metodo} {ruta} -> {respuesta.status_code}: "
                               f"{respuesta.text[:300]}")
        return respuesta.json() if respuesta.content else None


@pytest.fixture
def api(admin_client):
    return _ApiDeTest(admin_client)


def _contador():
    hechos = {}

    def contar(clave, nuevo):
        creados, existentes = hechos.get(clave, (0, 0))
        hechos[clave] = (creados + int(nuevo), existentes + int(not nuevo))

    return hechos, contar


def _revisores(api, usuario):
    return [u for u in _lista(api.get("/api/usuarios")) if u.get("username") == usuario]


# ── 🔴 La clave no vive en el repo ────────────────────────────────────────

def test_sin_credenciales_no_hay_revisor(api, monkeypatch, capsys):
    monkeypatch.delenv(ENV_REVISOR_USUARIO, raising=False)
    monkeypatch.delenv(ENV_REVISOR_PASSWORD, raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)

    sembrar(api)

    assert "sin revisor" in capsys.readouterr().out
    assert not [u for u in _lista(api.get("/api/usuarios"))
                if u.get("nombre") == "Revisor de integraciones"]


def test_con_credenciales_el_revisor_es_admin(api, monkeypatch):
    monkeypatch.setenv(ENV_REVISOR_USUARIO, "revisor-prueba")
    monkeypatch.setenv(ENV_REVISOR_PASSWORD, "clave-de-prueba-123")
    hechos, contar = _contador()

    _sembrar_revisor(api, contar)

    revisores = _revisores(api, "revisor-prueba")
    assert len(revisores) == 1
    assert revisores[0]["role"] == "admin"
    assert hechos["revisor"] == (1, 0)


def test_dos_corridas_no_lo_duplican_y_le_fijan_la_clave(api, monkeypatch):
    monkeypatch.setenv(ENV_REVISOR_USUARIO, "revisor-prueba")
    monkeypatch.setenv(ENV_REVISOR_PASSWORD, "clave-de-prueba-123")
    _, contar = _contador()
    _sembrar_revisor(api, contar)

    # La clave del archivo del VPS cambió: la segunda corrida la aplica.
    monkeypatch.setenv(ENV_REVISOR_PASSWORD, "otra-clave-456")
    hechos, contar = _contador()
    _sembrar_revisor(api, contar)

    revisores = _revisores(api, "revisor-prueba")
    assert len(revisores) == 1
    assert hechos["revisor"] == (0, 1)
    # 🔑 La prueba es que ENTRE, no que la fila exista: un cliente nuevo, sin la
    # sesión del admin, se loguea con la clave nueva y no con la vieja.
    otro = TestClient(app, base_url="https://testserver")
    assert otro.post("/api/login", json={"username": "revisor-prueba",
                                         "password": "otra-clave-456"}).status_code == 200
    otro = TestClient(app, base_url="https://testserver")
    assert otro.post("/api/login", json={"username": "revisor-prueba",
                                         "password": "clave-de-prueba-123"}).status_code == 401


# ── 🔴 El add-on, sólo en una demo ────────────────────────────────────────

def test_fuera_de_una_demo_no_toca_el_add_on(monkeypatch, capsys, admin_client):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    antes = db.get_modulos().get(ADDON_COPIA_EXTERNA)
    _, contar = _contador()

    _prender_copia_externa(contar)

    assert db.get_modulos().get(ADDON_COPIA_EXTERNA) == antes
    assert "no es una instancia demo" in capsys.readouterr().out


def test_en_una_demo_prende_la_copia_externa(monkeypatch, admin_client):
    monkeypatch.setenv("DEMO_MODE", "1")
    db.set_addon(ADDON_COPIA_EXTERNA, False)
    hechos, contar = _contador()

    _prender_copia_externa(contar)

    assert db.get_modulos().get(ADDON_COPIA_EXTERNA) is True
    assert hechos["add-ons"] == (1, 0)

    # Idempotente: la segunda vez ya estaba.
    hechos, contar = _contador()
    _prender_copia_externa(contar)
    assert hechos["add-ons"] == (0, 1)
