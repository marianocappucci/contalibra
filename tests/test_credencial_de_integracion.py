"""La credencial de integración (libraauth v0.52.0, su ADR-025; libracore ADR-071).

Otra instancia de la familia le mete datos a ésta por dos rutas:
`POST /api/integraciones/consultas` (MedLibra) y la ingesta de
`/api/comprobantes-pendientes` (LibraDesk). Desde esta versión entran con el
`LIBRA_INTEGRACION_TOKEN` de esta ContaLibra en `x-integracion-auth`, que es
**una por instancia** y no abre nada más.

Lo que se fija:

1. Con la variable puesta, la integración entra a esas dos rutas.
2. 🔴 **No entra a nada de lo que abre el token de servicio**: usuarios, el
   correo saliente, el reenvío y el tema. Esa es la razón de que sea otra
   credencial.
3. Sin la variable, el header no sirve (falla cerrado); un valor equivocado
   tampoco, y la anterior vale mientras dure la rotación.
4. El token de servicio sigue entrando a las dos rutas (el backoffice, y los
   emisores que todavía no rotaron), y el servicio no entra por el header de
   integración.
"""
import pytest
from libraauth.session_auth import (
    INTEGRACION_TOKEN_ANTERIOR_ENV,
    INTEGRACION_TOKEN_ENV,
    INTEGRACION_TOKEN_HEADER,
    SERVICE_TOKEN_ENV,
    SERVICE_TOKEN_HEADER,
)

TOKEN = "un-token-de-integracion-de-prueba-0123456789"
ANTERIOR = "la-integracion-anterior-de-prueba-0123456789"
SERVICIO = "un-token-de-servicio-de-prueba-0123456789"

CONSULTAS = "/api/integraciones/consultas"
INGESTA = "/api/comprobantes-pendientes"

#: Lo que el token de servicio abre (`test_token_de_servicio.py`, `test_tema.py`)
#: y la integración NO. GET, salvo el tema, que sólo se escribe.
CERRADAS_GET = ["/api/usuarios", "/api/config/smtp", "/api/config/reenvio-correo",
                "/api/integraciones/config", INGESTA]


def _consulta(referencia="turno-integracion-1") -> dict:
    return {
        "sistema": "medlibra",
        "referencia": referencia,
        "fecha": "2026-08-24",
        "descripcion": "Consulta",
        "importe": 2500.0,
        "medio_pago": "efectivo",
        "paciente": {"nombre": "Ana Gómez", "cuit": "", "condicion_iva": ""},
        "facturar": False,
    }


def _comprobante(origen_id="77") -> dict:
    return {
        "origen_producto": "libradesk",
        "origen_instancia": "ejemplo",
        "origen_tipo": "cuota_contrato",
        "origen_id": origen_id,
        "cliente_razon": "Ferretería Ejemplo",
        "cliente_cuit": "30-71234567-9",
        "items": [{"description": "Alquiler impresora", "qty": 1,
                   "unit_price": 45000.0, "iva_rate": 0.21}],
    }


@pytest.fixture
def sin_sesion(admin_client, monkeypatch):
    """El usuario de integraciones configurado por el admin, y después sin cookie:
    lo que sigue llega como llega otra instancia."""
    puesto = admin_client.put("/api/integraciones/config", json={"username": "admin"})
    assert puesto.status_code == 200, puesto.text
    admin_client.cookies.clear()
    monkeypatch.delenv(SERVICE_TOKEN_ENV, raising=False)
    monkeypatch.delenv(INTEGRACION_TOKEN_ANTERIOR_ENV, raising=False)
    monkeypatch.setenv(INTEGRACION_TOKEN_ENV, TOKEN)
    return admin_client


def _integ(valor=TOKEN) -> dict:
    return {INTEGRACION_TOKEN_HEADER: valor}


# ── 1. Entra a las dos rutas de integración ─────────────────────────────────

def test_la_integracion_registra_una_consulta(sin_sesion):
    r = sin_sesion.post(CONSULTAS, json=_consulta(), headers=_integ())
    assert r.status_code == 200, r.text
    # La venta se atribuye al usuario de integraciones de la instancia, no a
    # quien llama (la identidad `@integracion` no tiene `id`).
    assert r.json()["venta"]["usuario_id"] is not None


def test_la_integracion_deposita_un_comprobante(sin_sesion):
    r = sin_sesion.post(INGESTA, json=_comprobante(), headers=_integ())
    assert r.status_code == 201, r.text
    assert r.json()["creado"] is True


# ── 2. 🔴 Y a nada más ──────────────────────────────────────────────────────

def test_la_integracion_no_abre_usuarios_smtp_ni_la_bandeja(sin_sesion):
    for ruta in CERRADAS_GET:
        r = sin_sesion.get(ruta, headers=_integ())
        assert r.status_code in (401, 403), f"{ruta} -> {r.status_code}"


def test_la_integracion_no_escribe_el_tema(sin_sesion):
    r = sin_sesion.put("/api/tema", json={"tema": {}}, headers=_integ())
    assert r.status_code in (401, 403), r.status_code


def test_la_integracion_no_escribe_la_marca(sin_sesion):
    r = sin_sesion.put("/api/marca", json={"nombre": "Otra"}, headers=_integ())
    assert r.status_code in (401, 403), r.status_code


def test_la_integracion_no_cambia_el_usuario_de_integraciones(sin_sesion):
    r = sin_sesion.put("/api/integraciones/config", json={"username": "admin"}, headers=_integ())
    assert r.status_code in (401, 403), r.status_code


def test_control_el_servicio_si_abre_usuarios(sin_sesion, monkeypatch):
    """Sin este control, el test de arriba podría pasar porque las rutas no
    existen o piden otra cosa."""
    monkeypatch.setenv(SERVICE_TOKEN_ENV, SERVICIO)
    r = sin_sesion.get("/api/usuarios", headers={SERVICE_TOKEN_HEADER: SERVICIO})
    assert r.status_code == 200, r.status_code


# ── 3. Falla cerrado y rota sin corte ───────────────────────────────────────

def test_sin_la_variable_el_header_no_sirve(sin_sesion, monkeypatch):
    monkeypatch.delenv(INTEGRACION_TOKEN_ENV, raising=False)
    assert sin_sesion.post(CONSULTAS, json=_consulta(), headers=_integ()).status_code in (401, 403)
    assert sin_sesion.post(INGESTA, json=_comprobante(), headers=_integ()).status_code in (401, 403)


def test_un_valor_equivocado_no_entra(sin_sesion):
    r = sin_sesion.post(INGESTA, json=_comprobante(), headers=_integ("otro-valor"))
    assert r.status_code in (401, 403)


def test_la_anterior_vale_mientras_dura_la_rotacion(sin_sesion, monkeypatch):
    monkeypatch.setenv(INTEGRACION_TOKEN_ANTERIOR_ENV, ANTERIOR)
    assert sin_sesion.post(INGESTA, json=_comprobante("1"), headers=_integ(ANTERIOR)).status_code == 201
    assert sin_sesion.post(INGESTA, json=_comprobante("2"), headers=_integ(TOKEN)).status_code == 201
    monkeypatch.delenv(INTEGRACION_TOKEN_ANTERIOR_ENV)
    assert sin_sesion.post(INGESTA, json=_comprobante("3"), headers=_integ(ANTERIOR)).status_code in (401, 403)


# ── 4. El servicio sigue entrando, cada uno por su header ───────────────────

def test_el_servicio_sigue_entrando_a_las_dos_rutas(sin_sesion, monkeypatch):
    monkeypatch.setenv(SERVICE_TOKEN_ENV, SERVICIO)
    h = {SERVICE_TOKEN_HEADER: SERVICIO}
    assert sin_sesion.post(CONSULTAS, json=_consulta("turno-servicio"), headers=h).status_code == 200
    assert sin_sesion.post(INGESTA, json=_comprobante("srv"), headers=h).status_code == 201


def test_el_token_de_integracion_no_vale_como_servicio_ni_al_reves(sin_sesion, monkeypatch):
    monkeypatch.setenv(SERVICE_TOKEN_ENV, SERVICIO)
    assert sin_sesion.get("/api/usuarios", headers={SERVICE_TOKEN_HEADER: TOKEN}).status_code in (401, 403)
    assert sin_sesion.post(INGESTA, json=_comprobante(), headers=_integ(SERVICIO)).status_code in (401, 403)
