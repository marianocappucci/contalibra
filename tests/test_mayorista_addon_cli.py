"""Slice 5 del paquete mayorista: habilitar el add-on por instancia.

Dos capas:
- `db.set_addon(nombre, on)`: prende/apaga un módulo suelto en la instancia
  (corre dentro del contenedor, contra su PostgreSQL). Tests contra PostgreSQL.
- `scripts.panel_admin._addon`: el comando `panel_admin.py addon <slug> <addon>
  on|off` que valida contra `plans.ADDONS`, encuentra el cliente y corre
  `set_addon` por `docker exec`. Tests unitarios (se mockea `docker`).
"""
from app import database as db

# ── set_addon (contra PostgreSQL) ────────────────────────────────────────────

def test_set_addon_prende_y_apaga_el_modulo(client):
    assert db.get_modulos()["mayorista"] is False  # el seed lo deja apagado
    db.set_addon("mayorista", True)
    assert db.get_modulos()["mayorista"] is True
    db.set_addon("mayorista", False)
    assert db.get_modulos()["mayorista"] is False


def test_set_addon_crea_la_fila_si_falta(client):
    with db.get_connection() as conn:
        conn.execute("DELETE FROM modulos WHERE modulo=?", ("mayorista",))
    assert "mayorista" not in db.get_modulos()
    db.set_addon("mayorista", True)
    assert db.get_modulos()["mayorista"] is True


def test_set_addon_abre_el_gate_real(admin_client):
    """El efecto que importa: `require_module("mayorista")` deja pasar."""
    cid = db.create_client("Distribuidora")
    assert admin_client.get(f"/api/clientes/{cid}/lista-precio").status_code == 403
    db.set_addon("mayorista", True)
    assert admin_client.get(f"/api/clientes/{cid}/lista-precio").status_code == 200


# ── panel_admin.py addon (CLI, docker mockeado) ──────────────────────────────

def _pa():
    import scripts.panel_admin as pa
    return pa


def test_cli_rechaza_add_on_desconocido_y_estado_invalido():
    pa = _pa()
    assert pa._addon(["slug", "inexistente", "on"]) is False   # no está en ADDONS
    assert pa._addon(["slug", "mayorista", "quizas"]) is False  # on|off inválido
    assert pa._addon(["slug", "mayorista"]) is False            # faltan argumentos


def test_cli_cliente_inexistente_da_error(monkeypatch):
    pa = _pa()
    monkeypatch.setattr(pa, "find_client", lambda slug: None)
    assert pa._addon(["nope", "mayorista", "on"]) is False


def test_cli_corre_set_addon_en_el_contenedor(monkeypatch):
    pa = _pa()
    monkeypatch.setattr(pa, "find_client", lambda slug: {"container": "contalibra-micomercio"})

    llamadas = []

    class _R:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(cmd, **kw):
        llamadas.append(cmd)
        return _R()

    monkeypatch.setattr(pa.subprocess, "run", _fake_run)

    assert pa._addon(["micomercio", "mayorista", "on"]) is True
    cmd = llamadas[0]
    assert cmd[:3] == ["docker", "exec", "contalibra-micomercio"]
    assert cmd[3:5] == ["python3", "-c"]
    # El snippet importa el set_addon del contenedor y lo llama con True.
    assert "from app.database import set_addon" in cmd[-1]
    assert "set_addon('mayorista', True)" in cmd[-1]


def test_cli_off_pasa_false(monkeypatch):
    pa = _pa()
    monkeypatch.setattr(pa, "find_client", lambda slug: {"container": "contalibra-x"})
    codigos = []
    monkeypatch.setattr(pa.subprocess, "run",
                        lambda cmd, **kw: codigos.append(cmd[-1]) or type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    assert pa._addon(["x", "mayorista", "off"]) is True
    assert "set_addon('mayorista', False)" in codigos[0]


def test_cli_error_de_docker_devuelve_false(monkeypatch):
    pa = _pa()
    monkeypatch.setattr(pa, "find_client", lambda slug: {"container": "contalibra-x"})
    monkeypatch.setattr(pa.subprocess, "run",
                        lambda cmd, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": "boom"})())
    assert pa._addon(["x", "mayorista", "on"]) is False
