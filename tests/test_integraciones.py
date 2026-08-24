"""Consultas que llegan desde otro producto de la familia, para facturar acá.

🔴 **Lo que hay que probar no es que la venta se cree.** Lo caro son las tres
formas de crearla mal, y las tres son silenciosas:

1. **Sin usuario**, porque el token de servicio no es uno. La venta entra, suma
   su movimiento de caja y queda **fuera de todo turno**: el cierre no la ve.
2. **Dos veces**, porque el emisor reintentó. Dos ventas y dos facturas por una
   consulta, y la única señal es que a fin de mes no cierre.
3. **Con el comprobante equivocado**, porque los datos fiscales del paciente se
   ignoraron y todo salió Consumidor Final.

Cada uno tiene su test y su control al lado.
"""
import pytest
from fastapi.testclient import TestClient

from libraauth.session_auth import SERVICE_TOKEN_ENV, SERVICE_TOKEN_HEADER

from app import database as db

TOKEN = "un-token-de-servicio-de-prueba"


def _consulta(**cambios) -> dict:
    cuerpo = {
        "sistema": "medlibra",
        "referencia": "turno-abc-123",
        "fecha": "2026-08-24",
        "descripcion": "Consulta",
        "importe": 2500.0,
        "medio_pago": "efectivo",
        "paciente": {"nombre": "Ana Gómez", "cuit": "", "condicion_iva": ""},
        "facturar": False,
    }
    cuerpo.update(cambios)
    return cuerpo


@pytest.fixture
def configurado(admin_client: TestClient) -> TestClient:
    """Con el usuario de integraciones apuntando al admin de la instancia."""
    puesto = admin_client.put("/api/integraciones/config", json={"username": "admin"})
    assert puesto.status_code == 200, puesto.text
    return admin_client


def _mandar(client: TestClient, **cambios):
    return client.post("/api/integraciones/consultas", json=_consulta(**cambios))


# ── La configuración del usuario ───────────────────────────────────────────

def test_arranca_sin_usuario_configurado(admin_client: TestClient):
    assert admin_client.get("/api/integraciones/config").json() == {
        "usuario_integraciones": ""
    }


def test_no_se_puede_configurar_un_usuario_que_no_existe(admin_client: TestClient):
    """Configurar un username inexistente dejaría la integración *pareciendo*
    lista y fallando recién con la primera consulta."""
    rechazado = admin_client.put(
        "/api/integraciones/config", json={"username": "fantasma"},
    )
    assert rechazado.status_code == 422
    assert "fantasma" in rechazado.json()["detail"]


def test_vaciar_el_username_apaga_la_integracion(configurado: TestClient):
    configurado.put("/api/integraciones/config", json={"username": ""})
    apagado = _mandar(configurado)
    assert apagado.status_code == 409
    assert "usuario para integraciones" in apagado.json()["detail"]


# ── 1. Sin usuario, la venta no se crea ────────────────────────────────────

def test_sin_usuario_configurado_rechaza_en_vez_de_crear_la_venta(
    admin_client: TestClient,
):
    """🔴 **Falla cerrado.** Crear la venta sin `usuario_id` no rompe nada: entra,
    suma su movimiento de caja y queda fuera de todo turno. El descuadre se
    descubre a fin de mes."""
    rechazado = _mandar(admin_client)
    assert rechazado.status_code == 409
    assert db.get_all_ventas() == []


def test_con_usuario_configurado_la_venta_queda_a_su_nombre(configurado: TestClient):
    """🔴 El control, y lo que hace que la venta entre al turno de caja: el
    `usuario_id` no es una etiqueta de auditoría, es de dónde sale
    `get_turno_activo`."""
    creada = _mandar(configurado)
    assert creada.status_code == 200, creada.text
    venta = creada.json()["venta"]
    admin = db.get_usuario_by_username("admin")
    assert venta["usuario_id"] == admin["id"]
    assert venta["total"] == 2500.0
    assert venta["cliente_nombre"] == "Ana Gómez"


def test_la_venta_externa_entra_al_turno_de_caja_abierto(configurado: TestClient):
    """🔴 **Éste es el test que justifica todo el diseño.**

    La razón de que la instancia configure un usuario —en vez de dejar que el
    token de servicio cree la venta sin dueño— es exactamente ésta:
    `crear_venta_directa` engancha la venta al turno **a través del
    `usuario_id`**. Con `None` la venta entra igual, suma su movimiento de caja
    y queda huérfana de turno: el cierre no la ve y el descuadre aparece a fin
    de mes, sin nada que lo explique.
    """
    abierto = configurado.post("/api/turnos/abrir", json={"monto_inicial": 5000.0})
    assert abierto.status_code == 200, abierto.text
    turno_id = abierto.json()["id"]

    creada = _mandar(configurado)
    assert creada.json()["venta"]["turno_id"] == turno_id


def test_sin_turno_abierto_la_venta_entra_igual(configurado: TestClient):
    """🔴 El control por el otro lado: **no** se rechaza la consulta porque no
    haya turno. Un consultorio puede completar un turno fuera del horario de
    caja, y perder la venta sería peor que registrarla sin turno."""
    creada = _mandar(configurado)
    assert creada.status_code == 200
    assert creada.json()["venta"]["turno_id"] is None


def test_el_pedido_no_puede_elegir_a_quien_atribuirle_la_venta(
    configurado: TestClient,
):
    """🔴 Un `usuario_id` en el payload se ignora. Si se respetara, cualquiera
    con el token podría atribuirle ventas a cualquier usuario de la instancia."""
    creada = configurado.post(
        "/api/integraciones/consultas",
        json={**_consulta(), "usuario_id": 99999, "username": "otro"},
    )
    assert creada.status_code == 200, creada.text
    admin = db.get_usuario_by_username("admin")
    assert creada.json()["venta"]["usuario_id"] == admin["id"]


# ── 2. La idempotencia ─────────────────────────────────────────────────────

def test_la_misma_referencia_no_crea_una_segunda_venta(configurado: TestClient):
    """El emisor reintenta —un timeout, un deploy en el medio— y no puede
    terminar con dos ventas por una consulta."""
    primera = _mandar(configurado)
    segunda = _mandar(configurado)

    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert primera.json()["ya_existia"] is False
    assert segunda.json()["ya_existia"] is True
    assert segunda.json()["venta"]["id"] == primera.json()["venta"]["id"]
    assert len(db.get_all_ventas()) == 1


def test_otra_referencia_si_crea_otra_venta(configurado: TestClient):
    """🔴 El control. Sin esto, "devolver siempre la primera venta" haría pasar
    al test de arriba — y el consultorio facturaría una sola consulta por día."""
    _mandar(configurado, referencia="turno-abc-123")
    _mandar(configurado, referencia="turno-def-456")
    assert len(db.get_all_ventas()) == 2


def test_el_mismo_id_desde_otro_sistema_no_colisiona(configurado: TestClient):
    """La clave es `(sistema, referencia)`, no la referencia sola: dos productos
    pueden numerar sus turnos igual."""
    _mandar(configurado, sistema="medlibra", referencia="1")
    _mandar(configurado, sistema="gestiolibra", referencia="1")
    assert len(db.get_all_ventas()) == 2


def test_la_venta_queda_atada_a_su_referencia(configurado: TestClient):
    venta_id = _mandar(configurado).json()["venta"]["id"]
    origen = db.get_origen_de_venta(venta_id)
    assert origen["sistema"] == "medlibra"
    assert origen["referencia"] == "turno-abc-123"


# ── 3. El comprobante ──────────────────────────────────────────────────────

def test_sin_datos_fiscales_va_como_consumidor_final(configurado: TestClient):
    """Es el caso normal de un consultorio: no se crea cliente."""
    creada = _mandar(configurado)
    assert creada.json()["venta"]["cliente_id"] is None
    assert db.get_all_clients() == []


def test_con_cuit_se_crea_el_cliente_y_la_venta_va_a_su_nombre(
    configurado: TestClient,
):
    """Sin esto, un paciente Responsable Inscripto recibiría Factura B."""
    creada = _mandar(configurado, paciente={
        "nombre": "Clínica del Sur SRL",
        "cuit": "30711223344",
        "condicion_iva": "Responsable Inscripto",
    })
    cliente_id = creada.json()["venta"]["cliente_id"]
    assert cliente_id is not None
    cliente = db.get_client(cliente_id)
    assert cliente["cuit_dni"] == "30711223344"
    assert cliente["iva_condition"] == "Responsable Inscripto"


def test_un_cuit_que_ya_es_cliente_no_se_duplica(configurado: TestClient):
    """🔴 Se busca por CUIT y no por nombre: dos homónimos compartirían cuenta
    corriente y comprobantes, y el mismo paciente escrito distinto abriría un
    cliente nuevo cada vez."""
    paciente = {
        "nombre": "Clínica del Sur SRL",
        "cuit": "30711223344",
        "condicion_iva": "Responsable Inscripto",
    }
    primera = _mandar(configurado, referencia="t-1", paciente=paciente)
    # Mismo CUIT, el nombre escrito distinto.
    segunda = _mandar(
        configurado, referencia="t-2",
        paciente={**paciente, "nombre": "CLINICA DEL SUR S.R.L."},
    )
    assert primera.json()["venta"]["cliente_id"] == segunda.json()["venta"]["cliente_id"]
    assert len(db.get_all_clients()) == 1


# ── La facturación ─────────────────────────────────────────────────────────

def test_con_facturar_emite_el_comprobante(configurado: TestClient):
    """La suite corre con `ENV=development`, así que ARCA devuelve un CAE
    simulado por el mismo camino que dev.contalibra."""
    creada = _mandar(configurado, facturar=True)
    assert creada.status_code == 200, creada.text
    factura = creada.json()["factura"]
    assert factura is not None
    assert factura["total"] == 2500.0
    assert factura["cae"]


def test_reintentar_una_consulta_ya_facturada_no_emite_otra(configurado: TestClient):
    """🔴 Dos facturas por una consulta es el daño que no se puede deshacer:
    un CAE emitido no se borra, se anula con una nota de crédito."""
    primera = _mandar(configurado, facturar=True)
    segunda = _mandar(configurado, facturar=True)
    assert segunda.json()["ya_existia"] is True
    assert segunda.json()["factura"]["id"] == primera.json()["factura"]["id"]
    assert len(db.get_all_facturas()) == 1


def test_sin_facturar_queda_la_venta_cobrada_y_sin_comprobante(
    configurado: TestClient,
):
    creada = _mandar(configurado, facturar=False)
    venta = creada.json()["venta"]
    assert creada.json()["factura"] is None
    assert venta["factura_id"] is None
    # `estado` es el legible que arma `_venta_dict`; el crudo es `status`.
    assert venta["estado"] == "cobrada"
    # Y la plata entró igual: la venta sin comprobante no es una venta sin cobrar.
    assert venta["pagos"][0]["monto"] == 2500.0


# ── El token de servicio ───────────────────────────────────────────────────

def test_el_token_de_servicio_abre_consultas(client: TestClient, monkeypatch):
    """Es lo que le permite al producto emisor mandar sin ser usuario de esta
    instancia. Se configura primero como admin, porque `/config` NO lo acepta."""
    resp = client.post("/api/login", json={
        "username": "admin", "password": __import__("os").environ["ADMIN_PASSWORD"],
    })
    assert resp.status_code == 200
    client.put("/api/integraciones/config", json={"username": "admin"})
    client.post("/api/logout")

    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    creada = client.post(
        "/api/integraciones/consultas", json=_consulta(),
        headers={SERVICE_TOKEN_HEADER: TOKEN},
    )
    assert creada.status_code == 200, creada.text
    assert len(db.get_all_ventas()) == 1


def test_sin_token_ni_sesion_no_entra(client: TestClient, monkeypatch):
    """🔴 El control del de arriba: sin esto, "el endpoint está abierto" pasaría
    igual."""
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    sin_nada = client.post("/api/integraciones/consultas", json=_consulta())
    assert sin_nada.status_code in (401, 403)

    token_malo = client.post(
        "/api/integraciones/consultas", json=_consulta(),
        headers={SERVICE_TOKEN_HEADER: "otro-token"},
    )
    assert token_malo.status_code in (401, 403)


def test_el_token_de_servicio_NO_abre_la_configuracion(
    client: TestClient, monkeypatch,
):
    """🔴 Quién recibe las ventas externas lo decide el dueño de la caja, no
    quien tiene el token. Si el token pudiera reconfigurarlo, el permiso que se
    amplió para mandar consultas serviría para redirigir la caja."""
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    cabeceras = {SERVICE_TOKEN_HEADER: TOKEN}
    assert client.get("/api/integraciones/config", headers=cabeceras).status_code in (401, 403)
    assert client.put(
        "/api/integraciones/config", json={"username": "admin"}, headers=cabeceras,
    ).status_code in (401, 403)
