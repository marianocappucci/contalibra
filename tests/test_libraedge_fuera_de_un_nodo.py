"""Fuera de un nodo offline, LibraEdge no cambia nada (E6, 2026-10-19).

Contalibra tiene un cliente real (Compulibra) que no es ni va a ser un nodo: su instancia no tiene `LIBRAEDGE_NODE_ID`.
Lo que cambió en E6 —los ganchos con el outbox, el puerto de ventas con la conexión del nodo, el numerador, el detalle
de la venta, el ticket, las rutas `/api/nodo/*` y `/sync/v1/*` (desde libraedge ADR-014 sin adicional `offline`)— tiene que comportarse ahí
**exactamente como antes**. Cada test de acá es un camino que Compulibra usa todos los días: facturar una venta, la
bandeja de comprobantes, el cobro y la ingesta de ventas por integración.
"""
import datetime

import pytest
from libraauth.session_auth import SERVICE_TOKEN_ENV, SERVICE_TOKEN_HEADER

from app import database as db
from app import offline, venta_facturacion
from app.db_core import get_connection

HOY = datetime.date.today().isoformat()
TOKEN = "un-token-de-servicio-de-prueba"


@pytest.fixture(autouse=True)
def _sin_identidad_de_nodo(monkeypatch):
    """Una instancia común, como Compulibra: ninguna variable de LibraEdge."""
    for variable in ("LIBRAEDGE_NODE_ID", "CONTALIBRA_EDGE_NODE_ID", "LIBRAEDGE_PREFIJO", "LIBRAEDGE_ESTADO",
                     "LIBRAEDGE_CENTRAL_URL", "LIBRAEDGE_NODE_SECRET"):
        monkeypatch.delenv(variable, raising=False)


@pytest.fixture()
def nada_del_nodo(monkeypatch):
    """Si algo de lo del nodo se llamara fuera de un nodo, el test se entera."""

    async def numerar_en_el_nodo(*a, **kw):
        raise AssertionError("fuera de un nodo no se pide el ticket al central")

    monkeypatch.setattr(offline, "numerar_en_el_nodo", numerar_en_el_nodo)


def _venta(client, pagos=None, **extra):
    payload = {
        "fecha": HOY,
        "items": [{"nombre": "Mouse óptico", "qty": 2, "precio": 1500.0}],
        "pagos": pagos or [{"medio": "efectivo", "monto": 3000.0}],
    }
    payload.update(extra)
    r = client.post("/api/ventas", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _cuantas(tabla: str) -> int:
    with get_connection() as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0])


def _nada_encolado():
    assert _cuantas("sync_outbox") == 0, "fuera de un nodo no se encola nada para el central"
    assert _cuantas("local_sequences") == 0


def test_la_instancia_no_es_un_nodo():
    assert offline.nodo() is None and offline.nodo_local() is None
    assert venta_facturacion.PUERTO.conexion.es_nodo() is False
    assert venta_facturacion.PUERTO.conexion.sin_conexion() is False, "fuera de un nodo nunca está «sin conexión»"


def test_facturar_una_venta_numera_y_emite_como_siempre(admin_client, nada_del_nodo):
    venta = _venta(admin_client)
    assert not venta["numero"].startswith("S"), "fuera de un nodo el número no lleva prefijo de sucursal"
    r = admin_client.post(f"/api/ventas/{venta['id']}/facturar")
    assert r.status_code == 200, r.text
    factura = r.json()["factura"]
    assert factura["cae"]
    detalle = admin_client.get(f"/api/ventas/{venta['id']}").json()
    assert detalle["factura_id"] == factura["id"] and detalle["factura_pendiente"] is None
    assert _cuantas("comprobantes_pendientes") == 0, "nada va a la bandeja"
    _nada_encolado()


def test_el_detalle_es_el_del_motor_mas_factura_pendiente_en_null(admin_client):
    from libracommerce.erp import ventas as motor

    venta = _venta(admin_client, observaciones="detalle")
    detalle = admin_client.get(f"/api/ventas/{venta['id']}").json()
    with get_connection() as conn:
        del_motor = motor.obtener_venta(conn, venta["id"])
    assert set(detalle) == set(del_motor) | {"factura_pendiente"}
    assert detalle["factura_pendiente"] is None
    assert admin_client.get("/api/ventas/999999").status_code == 404
    assert admin_client.get("/api/ventas/medios-pago").status_code == 200, "sigue yendo al router del motor"


def test_el_ticket_no_dice_que_no_es_factura(admin_client, monkeypatch):
    from app import ticket_generator

    vistas = []
    real = ticket_generator.generar_ticket_venta
    monkeypatch.setattr(ticket_generator, "generar_ticket_venta",
                        lambda venta: vistas.append(venta.get("factura_pendiente")) or real(venta))
    venta = _venta(admin_client)
    assert admin_client.get(f"/ventas/{venta['id']}/ticket").status_code == 200
    assert vistas == [False]


def test_el_cobro_parcial_la_acreditacion_y_la_anulacion_no_encolan_nada(admin_client):
    parcial = _venta(admin_client, pagos=[{"medio": "efectivo", "monto": 1000.0}])
    assert parcial["estado"] == "parcial"
    cobrada = _venta(admin_client)
    assert admin_client.post(f"/api/ventas/{cobrada['id']}/anular").status_code == 200
    assert db.get_venta(cobrada["id"])["estado"] == "anulada"
    _nada_encolado()


def test_la_caja_a_mano_y_los_turnos_no_encolan_nada_y_el_arqueo_es_el_de_siempre(admin_client):
    """Abrir un turno, anotar y anular un movimiento y cerrar el turno (libracore ADR-076) pasan por
    `GANCHOS_DE_CAJA`: fuera de un nodo no encolan nada, y el cierre sigue arqueando contra las ventas del turno."""
    from libracore.ganchos_de_caja import GanchosDeCaja

    assert isinstance(offline.GANCHOS_DE_CAJA, GanchosDeCaja)
    tid = admin_client.post("/api/turnos/abrir", json={"monto_inicial": 1000.0}).json()["id"]
    venta = _venta(admin_client)
    with get_connection() as conn:
        db.vincular_venta_turno(venta["id"], tid, conn=conn)
        conn.commit()
    r = admin_client.post("/api/caja", json={
        "fecha": HOY, "tipo": "egreso", "concepto": "Librería", "monto": 200.0, "medio_pago": "efectivo"})
    assert r.status_code == 200, r.text
    assert admin_client.delete(f"/api/caja/{r.json()['id']}").status_code == 200
    r = admin_client.post(f"/api/turnos/{tid}/cerrar", json={"monto_declarado": 4000.0, "notas": "ok"})
    assert r.status_code == 200, r.text
    cerrado = r.json()
    assert cerrado["estado"] == "cerrado" and cerrado["notas"] == "ok"
    assert cerrado["monto_esperado_cierre"] == 4000.0, "1000 de apertura más los 3000 en efectivo de la venta del turno"
    _nada_encolado()


def test_las_rutas_del_nodo_dicen_que_no_es_un_nodo_y_no_hacen_nada(admin_client):
    assert admin_client.get("/api/nodo/conexion").json() == {
        "es_nodo": False, "en_linea": True, "node_id": None, "a_facturar": 0}
    r = admin_client.post("/api/nodo/facturar-pendientes")
    assert r.status_code == 200 and r.json()["es_nodo"] is False and r.json()["facturadas"] == []


def test_la_sincronizacion_esta_montada_pero_sin_nodos_no_entra_nadie(client):
    """Las rutas existen (no 404) y, sin ningún nodo registrado, ningún secreto vale."""
    cabeceras = {"Authorization": "Bearer secreto-ficticio"}
    operacion = {
        "operation_id": "nodo-ficticio:1", "node_id": "nodo-ficticio", "sequence": 1,
        "operation_type": "venta.registrada", "aggregate_type": "venta", "aggregate_id": "nodo-ficticio:venta:1",
        "occurred_at": "2026-10-19T12:00:00+00:00", "schema_version": 1, "payload": {},
    }
    assert client.post("/sync/v1/push", json=operacion, headers=cabeceras).status_code == 401
    assert client.get("/sync/v1/pull", params={"node_id": "nodo-ficticio"}, headers=cabeceras).status_code == 401
    assert client.post("/sync/v1/ticket-arca", json={"node_id": "nodo-ficticio"}, headers=cabeceras).status_code == 401
    assert _cuantas("sales") == 0


def test_al_arrancar_no_queda_ninguna_facturacion_automatica(client):
    from app.web import app as modulo_app

    assert modulo_app._parar_facturacion_al_volver is None, "fuera de un nodo no arranca el hilo de la bandeja"


def test_la_bandeja_y_la_ingesta_por_integracion_siguen_igual(admin_client, monkeypatch):
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    deposito = {
        "origen_producto": "libradesk", "origen_instancia": "ficticia", "origen_tipo": "cuota_contrato",
        "origen_id": "7", "cliente_razon": "Comercio Ficticio", "cliente_cuit": "20-00000000-1",
        "items": [{"description": "Abono", "qty": 1, "unit_price": 1000.0, "iva_rate": 0.21}],
    }
    r = admin_client.post("/api/comprobantes-pendientes", json=deposito, headers={SERVICE_TOKEN_HEADER: TOKEN})
    assert r.status_code == 201, r.text
    # Una venta del nodo no la puede depositar otro producto (la deja sólo el motor del nodo).
    r = admin_client.post("/api/comprobantes-pendientes", json={**deposito, "origen_tipo": "venta"},
                          headers={SERVICE_TOKEN_HEADER: TOKEN})
    assert r.status_code == 422
    bandeja = admin_client.get("/api/comprobantes-pendientes").json()
    assert [p["origen_tipo"] for p in bandeja["pendientes"]] == ["cuota_contrato"]
    r = admin_client.post("/api/comprobantes-pendientes/facturar-prefill", json={"ids": [bandeja["pendientes"][0]["id"]]})
    assert r.status_code == 200, r.text

    # La venta que llega por integración (MedLibra) entra como siempre: sin prefijo y sin nada encolado.
    assert admin_client.put("/api/integraciones/config", json={"username": "admin"}).status_code == 200
    r = admin_client.post("/api/integraciones/consultas", json={
        "sistema": "medlibra", "referencia": "turno-ficticio-1", "fecha": HOY, "descripcion": "Consulta",
        "importe": 2500.0, "medio_pago": "efectivo",
        "paciente": {"nombre": "Paciente Ficticio", "cuit": "", "condicion_iva": ""}, "facturar": False,
    })
    assert r.status_code == 200, r.text
    assert not r.json()["venta"]["numero"].startswith("S")
    _nada_encolado()


# ── LibraEdge incluido en todos los planes (libraedge ADR-014) ──────────


def test_el_offline_ya_no_es_un_adicional(admin_client, monkeypatch):
    from libracore import adicionales

    import plans

    assert "offline" not in adicionales.catalogo(plans) and "offline" not in plans.ADICIONALES
    assert "offline" not in plans.TODOS_LOS_MODULOS and "offline" not in plans.ADDONS
    assert "offline" not in db.get_modulos()  # una instancia nueva no lo siembra
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    listado = {a["clave"] for a in admin_client.get("/api/adicionales", headers={SERVICE_TOKEN_HEADER: TOKEN})
               .json()["adicionales"]}
    assert "offline" not in listado and {"mayorista", "resguardo_externo"} <= listado


def test_cualquier_instancia_registra_un_nodo_sin_contratar_nada(admin_client):
    from libraedge.aprovisionamiento import registrar, sin_guarda

    from app.offline import aprovisionamiento

    assert aprovisionamiento.verificar_alta is sin_guarda
    with get_connection() as conn:
        alta = registrar(conn, aprovisionamiento, "nodo-ficticio", "Casa central", salida=lambda _: None)
    assert alta.sucursal.nombre == "Casa central" and alta.prefijo
    assert set(alta.espejo) == set(offline.TABLAS_DE_REFERENCIA)
