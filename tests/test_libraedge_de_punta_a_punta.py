"""LibraEdge de punta a punta en Contalibra (E6, 2026-10-19): un nodo de mostrador y su central, **con dos bases**.

El nodo es la app de la suite sobre la base del worker, con la identidad de un nodo en el entorno. El central es una
**copia de esa base** hecha después de cargar la referencia (un producto, `arca_config`): es lo que deja el espejo de
LibraEdge, el central publica y el nodo tiene las mismas filas con las mismas claves. Lo que el nodo hace después
(ventas, facturas) sólo existe en la suya, y llega al central por las rutas `/sync/v1/*` reales del producto: el
transporte HTTP de LibraEdge está cableado al `TestClient` y, mientras dura cada pedido, la app apunta a la base del
central y no es un nodo.

ARCA y el WSAA son dobles (`arca_wsfe` y `arca_wsaa.autenticar`); todo lo demás es el código de verdad: el ticket que
presta el central (libraedge ADR-009), el numerador del nodo (libracore ADR-074), el outbox y los aplicadores
(libracommerce ADR-067 y ADR-068) y la costura del producto (`app/offline.py`). Es el mismo armado que el de
RestoLibra (`restolibra/tests/test_libraedge_de_punta_a_punta.py`), sin mesas: Contalibra vende en el mostrador.
"""
import datetime
import io
import json
import os
import urllib.error

import psycopg
import pytest

NODO = "nodo-e2e-1"
PREFIJO = "S02"
CENTRAL = "https://central.example"


def _ahora_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class _Escenario:
    def __init__(self, client, url_central, node_conn, secreto, ruta_estado):
        self.client = client
        self.url_central = url_central
        self.node_conn = node_conn
        self.secreto = secreto
        self.ruta_estado = ruta_estado
        self.autenticaciones = 0
        self.ultimo_cae = 0

    def bajar(self, espejo, altas) -> int:
        """Un ciclo de la bajada del espejo, con el reapuntado de las altas del nodo (libraedge ADR-021)."""
        from libraedge.db.repository import NodeRepository
        from libraedge.sync.esquema import version_de_alembic
        from libraedge.sync.pull import HttpPullTransport, MirrorApplier, PullWorker

        version = version_de_alembic(self.node_conn)
        worker = PullWorker(NodeRepository(self.node_conn),
                            HttpPullTransport(CENTRAL, NODO, self.secreto, version_esquema=version),
                            MirrorApplier(self.node_conn, espejo, node_id=NODO, altas=altas))
        aplicados = worker.run_once(NODO)
        self.node_conn.commit()
        return aplicados

    # ── la conexión del nodo con el central ──
    def en_linea(self, si: bool) -> None:
        with open(self.ruta_estado, "w", encoding="utf-8") as archivo:
            json.dump({"node_id": NODO, "en_linea": si, "ultima_sincronizacion_ok": _ahora_iso()}, archivo)

    def central(self):
        """Un context manager con la app apuntada al central y sin identidad de nodo."""
        return _EnElCentral(self.url_central)

    def subir(self):
        from libraedge.db.repository import NodeRepository
        from libraedge.sync.esquema import version_de_alembic
        from libraedge.sync.http import HttpSyncTransport
        from libraedge.sync.worker import OutboxWorker

        version = version_de_alembic(self.node_conn)
        worker = OutboxWorker(NodeRepository(self.node_conn), HttpSyncTransport(CENTRAL, self.secreto,
                                                                               version_esquema=version))
        resultado = worker.run_once()
        self.node_conn.commit()
        return resultado

    def en_revision_en_el_nodo(self):
        from libraedge.db.repository import NodeRepository

        return NodeRepository(self.node_conn).listar_en_revision()

    # ── el nodo vende en el mostrador ──
    def vender(self, monto=5000.0, pagado=None, fecha=None, qty=1, **venta):
        r = self.client.post("/api/ventas", json={
            "fecha": fecha or datetime.date.today().isoformat(),
            "items": [{"producto_id": self.producto["id"], "nombre": self.producto["nombre"], "qty": qty,
                       "precio": monto}],
            "pagos": [{"medio": "efectivo", "monto": monto * qty if pagado is None else pagado}],
            **venta,
        })
        assert r.status_code == 200, r.text
        return r.json()


class _EnElCentral:
    def __init__(self, url):
        self.url = url
        self.guardadas = {}

    def __enter__(self):
        from libracore.db import core

        for variable in ("LIBRAEDGE_NODE_ID", "LIBRAEDGE_PREFIJO"):
            self.guardadas[variable] = os.environ.pop(variable, None)
        core.configure(db_path=self.url, timeout=15)
        return self

    def __exit__(self, *exc):
        from libracore.db import core

        from app import db_core

        core.configure(db_path=db_core.DB_PATH, timeout=15)
        for variable, valor in self.guardadas.items():
            if valor is not None:
                os.environ[variable] = valor
        return False


class _Respuesta:
    def __init__(self, cuerpo):
        self._cuerpo = cuerpo

    def read(self):
        return self._cuerpo

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _cable(escenario):
    """`urlopen` de LibraEdge apuntado a la app real, que mientras contesta es el central."""

    def urlopen(pedido, timeout=None):
        ruta = pedido.full_url.replace(CENTRAL, "")
        cabeceras = dict(pedido.header_items())
        with escenario.central():
            if pedido.get_method() == "POST":
                r = escenario.client.post(ruta, content=pedido.data, headers=cabeceras)
            else:
                r = escenario.client.get(ruta, headers=cabeceras)
        if r.status_code >= 400:
            raise urllib.error.HTTPError(pedido.full_url, r.status_code, "error", {}, io.BytesIO(r.content))
        return _Respuesta(r.content)

    return urlopen


@pytest.fixture()
def escenario(admin_client, monkeypatch, tmp_path):
    from libracommerce.migrar import upgrade as migrar_libracommerce
    from libracore import arca_credenciales, arca_wsaa, arca_wsfe
    from libracore.db import arca_config as db_arca
    from libracore.respaldo_postgres import con_base
    from libraedge.db.repository import NodeRepository
    from libraedge.sync import http as http_module
    from libraedge.sync import pull as pull_module
    from libraedge.sync import ticket as ticket_module

    from app import db_core, db_usuarios, offline
    from app.db_core import get_connection

    # El deploy migra la cadena de LibraCommerce (`libracommerce-migrar upgrade --prefijo contalibra`), pero `init_db()` sólo trae su
    # baseline congelada: sin la revisión 0008 (`stock_movements.origen`/`origen_id`, libracommerce ADR-071) el central no puede
    # aplicar `stock.movimiento`. Se migra la base del nodo ANTES de copiarla al central, como están las dos en producción.
    migrar_libracommerce(db_core.DB_PATH)

    # La referencia que el central publica y el nodo espeja: un producto con stock y ARCA (datos ficticios).
    producto = admin_client.post("/api/productos", json={
        "nombre": "Cable UTP", "precio_venta": 5000.0, "precio_costo": 3000.0}).json()
    assert admin_client.post(f"/api/stock/{producto['id']}/ajuste",
                             json={"modo": "absoluto", "cantidad": 50}).status_code == 200
    db_arca.crear_arca_config("Comercio Ficticio", "20000000001", 3, "", "", ambiente="homologacion")
    # Un segundo depósito de la misma sucursal, para las transferencias del nodo (libracommerce ADR-071).
    camioneta = admin_client.post("/api/depositos", json={"nombre": "Camioneta"}).json()

    # El central: una copia de la base en este momento.
    worker = db_core.DB_PATH.rsplit("/", 1)[1].split("?")[0]
    nombre_central = f"{worker}_central"
    original = os.environ["_LIBRACORE_PG_CONTALIBRA_ORIGINAL"].replace("postgresql+psycopg://", "postgresql://")
    db_usuarios._engine.dispose()
    with psycopg.connect(original, autocommit=True) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{nombre_central}" WITH (FORCE)')
        admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s"
                      " AND pid <> pg_backend_pid() AND usename = current_user", (worker,))
        admin.execute(f'CREATE DATABASE "{nombre_central}" TEMPLATE "{worker}"')
    url_central = con_base(os.environ["_LIBRACORE_PG_CONTALIBRA_ORIGINAL"], nombre_central)

    # El alta del nodo, en el central: su secreto.
    with _EnElCentral(url_central), get_connection() as conn:
        secreto = NodeRepository(conn).register_node(NODO, branch_id="1")
        conn.commit()

    ruta_estado = str(tmp_path / "estado.json")
    for variable, valor in {"LIBRAEDGE_NODE_ID": NODO, "LIBRAEDGE_PREFIJO": PREFIJO, "LIBRAEDGE_ESTADO": ruta_estado,
                            "LIBRAEDGE_CENTRAL_URL": CENTRAL, "LIBRAEDGE_NODE_SECRET": secreto}.items():
        monkeypatch.setenv(variable, valor)
    monkeypatch.setattr(offline, "_cliente_de_ticket", None)

    node_conn = get_connection()
    esc = _Escenario(admin_client, url_central, node_conn, secreto, ruta_estado)
    esc.producto = producto
    esc.camioneta = camioneta
    esc.principal = next(d for d in admin_client.get("/api/depositos").json() if d["id"] != camioneta["id"])
    esc.en_linea(True)

    cable = _cable(esc)
    monkeypatch.setattr(http_module, "urlopen", cable)
    monkeypatch.setattr(ticket_module, "urlopen", cable)
    monkeypatch.setattr(pull_module, "urlopen", cable)

    # ARCA, de mentira: el WSAA del central (con el certificado «en disco») y el WSFE del nodo.
    async def autenticar(cert, clave, ambiente, servicio):
        esc.autenticaciones += 1
        vence = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=12)
        return {"token": "TOKEN-FICTICIO", "sign": "SIGN-FICTICIO", "expiracion": vence.isoformat()}

    async def ultimo_numero_autorizado(pv, tipo, cuit, token, sign, ambiente):
        assert token == "TOKEN-FICTICIO", "el nodo tiene que firmar con el ticket que prestó el central"
        return esc.ultimo_cae

    async def solicitar_cae(factura, cuit, token, sign, ambiente):
        esc.ultimo_cae += 1
        return {"cae": f"7000000000{esc.ultimo_cae:04d}", "cae_vto": "20261231"}

    monkeypatch.setattr(arca_credenciales, "paths_en_disco", lambda arca: ("cert-ficticio", "clave-ficticia"))
    monkeypatch.setattr(arca_wsaa, "autenticar", autenticar)
    monkeypatch.setattr(arca_wsfe, "ultimo_numero_autorizado", ultimo_numero_autorizado)
    monkeypatch.setattr(arca_wsfe, "solicitar_cae", solicitar_cae)

    yield esc

    node_conn.close()
    with psycopg.connect(original, autocommit=True) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{nombre_central}" WITH (FORCE)')


def _en_el_central(esc, sql, params=()):
    from app.db_core import get_connection

    with esc.central(), get_connection() as conn:
        return [tuple(f) for f in conn.execute(sql, params).fetchall()]


def _venta_del_central(esc, venta_id_nodo):
    filas = _en_el_central(
        esc, "SELECT id, number, status_detail FROM sales WHERE source_type = ? AND source_id = ?",
        (f"libraedge:{NODO}", venta_id_nodo))
    assert len(filas) == 1, f"la venta {venta_id_nodo} del nodo está {len(filas)} veces en el central"
    return filas[0]


def _stock_del_central(esc, producto_id) -> float:
    filas = _en_el_central(esc, "SELECT COALESCE(SUM(quantity_delta), 0) FROM stock_movements WHERE item_id = ?",
                           (producto_id,))
    return float(filas[0][0])


def test_las_ventas_de_mostrador_suben_cobradas_y_parciales_con_el_prefijo_del_nodo(escenario):
    esc = escenario
    cobrada = esc.vender(qty=2)
    parcial = esc.vender(monto=8000.0, pagado=3000.0)
    assert cobrada["numero"].startswith(f"{PREFIJO}-"), "en el nodo el número lleva el prefijo de la sucursal"
    assert parcial["estado"] == "parcial"

    esc.subir()
    assert esc.en_revision_en_el_nodo() == ()

    vid, numero, estado = _venta_del_central(esc, cobrada["id"])
    assert numero == cobrada["numero"] and estado == "cobrada"
    # La parcial también subió (decisión 5), con lo que se cobró.
    vid_parcial, _, estado = _venta_del_central(esc, parcial["id"])
    assert estado == "parcial"
    # La caja del central: lo acreditado de las dos.
    caja = _en_el_central(esc, "SELECT COALESCE(SUM(monto), 0) FROM caja_movimientos WHERE tipo = 'ingreso'")
    assert float(caja[0][0]) == 10000.0 + 3000.0
    # El stock que vendió el nodo también baja en el central: 50 del ajuste, menos 2 y 1.
    assert _stock_del_central(esc, esc.producto["id"]) == 47.0

    # Un segundo ciclo no repite nada.
    esc.subir()
    assert len(_en_el_central(esc, "SELECT id FROM sales")) == 2
    assert vid != vid_parcial


def test_un_cliente_dado_de_alta_en_el_nodo_sube_antes_que_su_venta_y_queda_con_el_id_del_central(escenario):
    """Altas de clientes en el nodo (libracore ADR-077, libracommerce ADR-070, libraedge ADR-021): el cajero da de alta un
    cliente por `POST /api/clientes` sin ver al central, le vende, y suben `cliente.alta` y `venta.registrada` en ese orden.
    El central crea al cliente con **su** id, la venta queda a su nombre y, cuando el id definitivo baja por el espejo, el
    nodo reapunta la venta y borra el provisorio."""
    esc = escenario
    from libraedge import aprovisionamiento as aprov
    from libraedge.db.repository import NodeRepository

    from app import offline

    # El central publica la referencia (el trigger del mapeo tiene que estar antes del alta que lo escribe).
    with esc.central():
        from app.db_core import get_connection

        with get_connection() as conn:
            assert aprov.publicar(conn, offline.aprovisionamiento, salida=lambda _: None) == 0
            espejo = aprov.espejo_del_nodo(conn, offline.aprovisionamiento)

    r = esc.client.post("/api/clientes", json={"name": "Cliente Nodo Ficticio", "cuit_dni": "20-00000002-8"})
    assert r.status_code in (200, 201), r.text
    provisorio = r.json()["id"]
    assert provisorio < 0, "en un nodo el alta lleva un id provisorio negativo, no el de la secuencia del nodo"
    venta = esc.vender(cliente_id=provisorio)

    operaciones = NodeRepository(esc.node_conn).list_pending_operations()
    esc.node_conn.commit()
    assert [op.operation_type for op in operaciones] == ["cliente.alta", "venta.registrada"]
    assert operaciones[0].aggregate_id == f"{NODO}:cliente:{provisorio}"
    assert operaciones[0].payload["cliente_id"] == operaciones[1].payload["cliente_id"] == provisorio

    resultado = esc.subir()
    assert resultado.confirmadas == 2 and esc.en_revision_en_el_nodo() == ()
    central = _en_el_central(esc, "SELECT id FROM clients WHERE name = ?", ("Cliente Nodo Ficticio",))
    assert len(central) == 1 and central[0][0] > 0, "el central le asigna su id (positivo, el de su secuencia)"
    id_central = central[0][0]
    vid = _venta_del_central(esc, venta["id"])[0]
    assert _en_el_central(esc, "SELECT customer_party_id FROM sales WHERE id = ?", (vid,)) == [(id_central,)], (
        "la venta queda a nombre del cliente, con su id del central")
    assert _en_el_central(esc, "SELECT id FROM parties WHERE id = ?", (id_central,)) == [(id_central,)]

    # Un segundo ciclo no repite nada: ni el cliente ni la venta.
    assert esc.subir().confirmadas == 0
    assert len(_en_el_central(esc, "SELECT id FROM clients WHERE name = ?", ("Cliente Nodo Ficticio",))) == 1

    # El id definitivo baja por el espejo: el nodo reapunta lo que tenía a nombre del provisorio y borra su fila.
    assert esc.bajar(espejo, offline.aprovisionamiento.altas) > 0
    en_el_nodo = lambda sql, *p: [tuple(f) for f in esc.node_conn.execute(sql, p).fetchall()]  # noqa: E731
    assert en_el_nodo("SELECT id FROM clients WHERE id = ?", provisorio) == []
    assert en_el_nodo("SELECT name FROM clients WHERE id = ?", id_central) == [("Cliente Nodo Ficticio",)]
    assert en_el_nodo("SELECT customer_party_id FROM sales WHERE id = ?", venta["id"]) == [(id_central,)]
    esc.node_conn.commit()


def test_con_internet_el_nodo_factura_con_el_ticket_prestado_y_la_factura_sube(escenario):
    esc = escenario
    venta = esc.vender()

    r = esc.client.post(f"/api/ventas/{venta['id']}/facturar")
    assert r.status_code == 200, r.text
    factura = r.json()["factura"]
    assert factura["cae"] and factura["numero"] == 1 and factura["punto_venta"] == 3
    # Facturar dos veces no emite otra: devuelve la misma.
    r = esc.client.post(f"/api/ventas/{venta['id']}/facturar")
    assert r.status_code == 200 and r.json()["factura"]["id"] == factura["id"]
    assert esc.autenticaciones == 1, "el central autentica una vez y el nodo guarda el ticket hasta que vence"

    esc.subir()
    assert esc.en_revision_en_el_nodo() == ()
    vid, _, _ = _venta_del_central(esc, venta["id"])
    en_el_central = _en_el_central(
        esc, "SELECT f.numero, f.cae, f.punto_venta FROM venta_links vl JOIN facturas f ON f.id = vl.factura_id"
             " WHERE vl.venta_id = ?", (vid,))
    assert en_el_central == [(1, factura["cae"], 3)], "la factura del nodo sube con su número y su CAE"


def test_sin_conexion_va_a_la_bandeja_y_al_volver_sale_con_la_fecha_de_la_venta(escenario):
    esc = escenario
    hace_dos = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
    venta = esc.vender(fecha=hace_dos)

    esc.en_linea(False)
    r = esc.client.post(f"/api/ventas/{venta['id']}/facturar")
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "factura_pendiente", r.text
    detalle = esc.client.get(f"/api/ventas/{venta['id']}").json()
    assert detalle["factura_pendiente"] is not None, "la pantalla tiene que poder decir «se factura al volver»"
    assert esc.client.get("/api/nodo/conexion").json() == {
        "es_nodo": True, "en_linea": False, "node_id": NODO, "a_facturar": 1}
    assert esc.autenticaciones == 0, "sin conexión no se sale a pedir el ticket"
    # La fila de la bandeja es una venta del nodo: la pantalla no la deja juntar en el formulario.
    pendientes = esc.client.get("/api/comprobantes-pendientes").json()["pendientes"]
    assert [(p["origen_tipo"], p["origen_producto"], p["origen_id"]) for p in pendientes] == [
        ("venta", "contalibra", str(venta["id"]))]
    r = esc.client.post("/api/comprobantes-pendientes/facturar-prefill", json={"ids": [pendientes[0]["id"]]})
    assert r.status_code == 409 and r.json()["detail"]["codigo"] == "se_factura_desde_la_venta"
    # Facturar ahora sin conexión, 409 (el botón de la bandeja está apagado).
    assert esc.client.post("/api/nodo/facturar-pendientes").status_code == 409
    # El ticket lo dice.
    ticket = esc.client.get(f"/ventas/{venta['id']}/ticket")
    assert ticket.status_code == 200

    # Vuelve la conexión: la bandeja se factura (lo mismo que hace sola la tanda de cada minuto).
    esc.en_linea(True)
    r = esc.client.post("/api/nodo/facturar-pendientes")
    assert r.status_code == 200, r.text
    detalle = esc.client.get(f"/api/ventas/{venta['id']}").json()
    assert detalle["factura_pendiente"] is None and detalle["factura_id"]
    fecha = r.json()["facturadas"][0]
    from libracore.db import facturas as db_facturas

    assert db_facturas.get_factura(fecha["factura_id"])["fecha"] == hace_dos, (
        "la factura al volver lleva la fecha de la venta (dentro de los 5 días de ARCA)")

    esc.subir()
    vid, _, _ = _venta_del_central(esc, venta["id"])
    assert _en_el_central(esc, "SELECT f.fecha FROM venta_links vl JOIN facturas f ON f.id = vl.factura_id"
                               " WHERE vl.venta_id = ?", (vid,)) == [(hace_dos,)]


def test_el_ticket_sin_conexion_dice_que_no_es_factura(escenario, monkeypatch):
    from app import ticket_generator

    vistas = []
    real = ticket_generator.generar_ticket_venta
    monkeypatch.setattr(ticket_generator, "generar_ticket_venta",
                        lambda venta: vistas.append(venta.get("factura_pendiente")) or real(venta))
    esc = escenario
    venta = esc.vender()
    esc.en_linea(False)
    assert esc.client.post(f"/api/ventas/{venta['id']}/facturar").status_code == 409
    assert esc.client.get(f"/ventas/{venta['id']}/ticket").status_code == 200
    otra = esc.vender()
    assert esc.client.get(f"/ventas/{otra['id']}/ticket").status_code == 200
    assert vistas == [True, False], "sólo la venta que espera en la bandeja lleva «no válido como factura»"


def test_la_anulacion_sube_y_lo_facturado_no_se_anula_sin_conexion(escenario):
    esc = escenario
    sin_factura = esc.vender()
    facturada = esc.vender(monto=7000.0)
    assert esc.client.post(f"/api/ventas/{facturada['id']}/facturar").status_code == 200

    assert esc.client.post(f"/api/ventas/{sin_factura['id']}/anular").status_code == 200
    esc.en_linea(False)
    r = esc.client.post(f"/api/ventas/{facturada['id']}/anular")
    assert r.status_code == 409, "anular lo facturado sin conexión está prohibido (libracommerce ADR-067)"

    esc.subir()
    assert _venta_del_central(esc, sin_factura["id"])[2] == "anulada"
    assert _venta_del_central(esc, facturada["id"])[2] == "cobrada"
    from libraedge.db.repository import NodeRepository

    from app.db_core import get_connection

    with get_connection() as conn:
        tipos = sorted(op.operation_type for op in NodeRepository(conn).list_pending_operations())
    assert tipos == [], f"quedó algo sin subir: {tipos}"


def test_un_nodo_dado_de_baja_no_recibe_el_ticket_y_no_va_a_la_bandeja(escenario):
    """El rechazo del central (`TicketRechazado`) es 422 `nodo_sin_arca`: no se arregla solo al volver la conexión,
    así que no se deja en la bandeja para reintentar."""
    from libraedge.db.repository import NodeRepository

    from app.db_core import get_connection

    esc = escenario
    with esc.central(), get_connection() as conn:
        NodeRepository(conn).deactivate_node(NODO)
        conn.commit()
    venta = esc.vender()
    r = esc.client.post(f"/api/ventas/{venta['id']}/facturar")
    assert r.status_code == 422 and r.json()["detail"]["codigo"] == "nodo_sin_arca", r.text
    assert esc.client.get(f"/api/ventas/{venta['id']}").json()["factura_pendiente"] is None


# ── La caja del nodo sube al central (libracore ADR-076, libracommerce ADR-069) ─────────────────────────────────────


def _operaciones_sin_subir(esc) -> list[str]:
    from libraedge.db.repository import NodeRepository

    from app.db_core import get_connection

    with get_connection() as conn:
        return [op.operation_type for op in NodeRepository(conn).list_pending_operations()]


def test_la_caja_del_nodo_se_encola_y_sube_al_central_sin_duplicar_lo_de_la_venta(escenario):
    """Abrir el turno, anotar un movimiento a mano, anularlo, una venta y cerrar el turno: el nodo encola en ese orden
    y el central reproduce todo, con el `origen` del nodo y sin duplicar la caja de la venta (que sube con la venta)."""
    esc = escenario
    hoy = datetime.date.today().isoformat()

    r = esc.client.post("/api/turnos/abrir", json={"monto_inicial": 1000.0, "notas": "mañana"})
    assert r.status_code == 200, r.text
    turno = r.json()["id"]
    r = esc.client.post("/api/caja", json={
        "fecha": hoy, "tipo": "egreso", "concepto": "Librería", "monto": 200.0, "medio_pago": "efectivo"})
    assert r.status_code == 200, r.text
    anulado = r.json()["id"]
    assert esc.client.delete(f"/api/caja/{anulado}").status_code == 200
    r = esc.client.post("/api/caja", json={
        "fecha": hoy, "tipo": "ingreso", "concepto": "Cambio", "monto": 500.0, "medio_pago": "efectivo"})
    assert r.status_code == 200, r.text
    conservado = r.json()["id"]
    venta = esc.vender()
    from app import database as db
    from app.db_core import get_connection

    with get_connection() as conn:
        db.vincular_venta_turno(venta["id"], turno, conn=conn)
        conn.commit()
    r = esc.client.post(f"/api/turnos/{turno}/cerrar", json={"monto_declarado": 6000.0, "notas": "cerrado"})
    assert r.status_code == 200, r.text

    assert _operaciones_sin_subir(esc) == [
        "turno.abierto", "caja.movimiento", "caja.movimiento_anulado", "caja.movimiento", "venta.registrada",
        "turno.cerrado"], "en el orden en que ocurrieron, y la caja de la venta no es un caja.movimiento"

    esc.subir()
    assert esc.en_revision_en_el_nodo() == ()
    assert _operaciones_sin_subir(esc) == []

    turnos = _en_el_central(
        esc, "SELECT estado, monto_inicial, monto_declarado_cierre, origen, origen_id FROM turnos_caja")
    assert turnos == [("cerrado", 1000.0, 6000.0, NODO, turno)]
    movimientos = _en_el_central(
        esc, "SELECT tipo, monto, anulado, origen_id FROM caja_movimientos WHERE origen = ? ORDER BY origen_id",
        (NODO,))
    assert movimientos == [("egreso", 200.0, 1, anulado), ("ingreso", 500.0, 0, conservado)]
    de_la_venta = _en_el_central(esc, "SELECT COUNT(*) FROM caja_movimientos WHERE origen IS NULL")
    assert de_la_venta == [(1,)], "la caja de la venta la escribe el central al aplicar la venta, una sola vez"

    esc.subir()
    assert _en_el_central(esc, "SELECT COUNT(*) FROM turnos_caja") == [(1,)]
    assert _en_el_central(esc, "SELECT COUNT(*) FROM caja_movimientos WHERE origen = ?", (NODO,)) == [(2,)]


def test_el_central_no_encola_su_propia_caja(escenario):
    """La misma app en el central (sin identidad de nodo) abre y cierra turnos como siempre y no encola nada."""
    from app.db_core import get_connection

    esc = escenario
    with esc.central():
        r = esc.client.post("/api/turnos/abrir", json={"monto_inicial": 100.0})
        assert r.status_code == 200, r.text
        turno = r.json()["id"]
        assert esc.client.post(f"/api/turnos/{turno}/cerrar", json={"monto_declarado": 100.0}).status_code == 200
        with get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM sync_outbox").fetchone()[0] == 0


# ── El reparto de autoridad (las tablas de referencia) ───────────────────


def test_las_tablas_de_referencia_existen_tienen_clave_y_no_apuntan_afuera(client):
    """Lo que el central publica tiene que poder sembrarse en el nodo: cada tabla existe, tiene clave primaria y sus
    FK apuntan sólo a otras tablas de referencia (si no, la siembra choca con una FK que el nodo no tiene)."""
    from libraedge.aprovisionamiento import clave_primaria, plan_de_publicacion

    from app.db_core import get_connection
    from app.offline import TABLAS_DE_REFERENCIA, aprovisionamiento

    with get_connection() as conn:
        for tabla in sorted(TABLAS_DE_REFERENCIA):
            assert clave_primaria(conn, tabla), f"{tabla}: sin clave primaria no se puede espejar"
        marcadores = ", ".join("?" * len(TABLAS_DE_REFERENCIA))
        fks = conn.execute(
            "SELECT tc.table_name, ccu.table_name FROM information_schema.table_constraints tc"
            " JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name"
            f" WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name IN ({marcadores})",
            tuple(sorted(TABLAS_DE_REFERENCIA)),
        ).fetchall()
        afuera = sorted({(f[0], f[1]) for f in fks if f[1] not in TABLAS_DE_REFERENCIA})
        assert afuera == [], f"tablas de referencia con FK hacia tablas que el nodo no espeja: {afuera}"
        plan = plan_de_publicacion(conn, aprovisionamiento)
    assert plan.faltantes == () and plan.salteadas == ()
    # Más `libraedge_mapeo`, que suma solo la declaración de altas en el nodo (libraedge ADR-021).
    assert {t for t, _ in plan.publicables} == set(TABLAS_DE_REFERENCIA) | {"libraedge_mapeo"}


# ── El stock de la sucursal del nodo (libracommerce ADR-071, libraedge ADR-023) ─────────────────────────────────────
#
# Decisiones del humano (2026-10-21): al vincular, el nodo trae las existencias de su sucursal; desde ahí el stock de esa
# sucursal lo mueve sólo el nodo (el central contesta 409); las transferencias son sólo dentro de la sucursal. Contalibra
# no tiene compras ni recepciones: la entrada de mercadería es el ajuste en modo «entrada».


def _stock_en_el_nodo(esc, producto_id) -> float:
    r = esc.client.get(f"/api/stock/{producto_id}")
    assert r.status_code == 200, r.text
    return float(r.json()["stock_actual"])


def _stock_del_central_en(esc, producto_id, deposito_id) -> float:
    filas = _en_el_central(
        esc, "SELECT COALESCE(SUM(quantity_delta), 0) FROM stock_movements WHERE item_id = ? AND location_id = ?",
        (producto_id, deposito_id))
    return float(filas[0][0])


def _ajustar(client, producto_id, **cuerpo):
    return client.post(f"/api/stock/{producto_id}/ajuste", json=cuerpo)


def test_un_ajuste_de_stock_del_nodo_sube_como_stock_movimiento_y_el_central_lo_aplica(escenario):
    esc = escenario
    pid = esc.producto["id"]
    assert _ajustar(esc.client, pid, modo="entrada", cantidad=10, referencia="Llegó mercadería").status_code == 200
    assert _ajustar(esc.client, pid, modo="salida", cantidad=4, referencia="Uso interno").status_code == 200
    assert _stock_en_el_nodo(esc, pid) == 56.0
    assert _operaciones_sin_subir(esc) == ["stock.movimiento", "stock.movimiento"], (
        "cada fila del ledger que no es de una venta sube como stock.movimiento")

    esc.subir()
    assert esc.en_revision_en_el_nodo() == ()
    assert _operaciones_sin_subir(esc) == []
    assert _stock_del_central(esc, pid) == 56.0, "50 del alta, más 10 y menos 4"
    # El central guarda de dónde vino cada fila: el nodo y su id. Es lo que lo vuelve idempotente.
    filas = _en_el_central(
        esc, "SELECT quantity_delta, origen, reason_code FROM stock_movements WHERE origen = ? ORDER BY origen_id",
        (NODO,))
    assert filas == [(10.0, NODO, "entrada"), (-4.0, NODO, "salida")]

    # Un segundo ciclo no repite nada.
    esc.subir()
    assert _stock_del_central(esc, pid) == 56.0
    assert len(_en_el_central(esc, "SELECT id FROM stock_movements WHERE origen = ?", (NODO,))) == 2


def test_una_venta_del_nodo_no_sube_tambien_como_stock_movimiento(escenario):
    """La salida de la venta viaja con `venta.registrada`: subirla además como movimiento descontaría el stock dos veces."""
    esc = escenario
    esc.vender(qty=2)
    assert _operaciones_sin_subir(esc) == ["venta.registrada"]
    esc.subir()
    assert _stock_del_central(esc, esc.producto["id"]) == 48.0


def test_una_transferencia_dentro_de_la_sucursal_sube_las_dos_patas_y_el_central_las_empareja(escenario):
    esc = escenario
    pid = esc.producto["id"]
    r = esc.client.post("/api/depositos/transferir", json={
        "producto_id": pid, "origen_id": esc.principal["id"], "destino_id": esc.camioneta["id"], "cantidad": 15})
    assert r.status_code == 200, r.text
    assert _operaciones_sin_subir(esc) == ["stock.movimiento", "stock.movimiento"]

    esc.subir()
    assert esc.en_revision_en_el_nodo() == ()
    assert _stock_del_central_en(esc, pid, esc.principal["id"]) == 35.0
    assert _stock_del_central_en(esc, pid, esc.camioneta["id"]) == 15.0
    assert _stock_del_central(esc, pid) == 50.0, "una transferencia no crea ni destruye mercadería"


def test_el_central_contesta_409_a_todo_lo_que_mueve_el_stock_de_una_sucursal_con_nodo(escenario):
    """La misma app sin identidad de nodo (el central): ajustes, transferencias y ventas desde la web son 409, con el código
    del motor, y no dejan nada escrito. Al dar de baja el nodo, el central vuelve a poder moverlo."""
    esc = escenario
    pid = esc.producto["id"]
    antes = _stock_del_central(esc, pid)
    ventas_antes = _en_el_central(esc, "SELECT COUNT(*) FROM sales")
    with esc.central():
        ajuste = _ajustar(esc.client, pid, modo="entrada", cantidad=5)
        transferencia = esc.client.post("/api/depositos/transferir", json={
            "producto_id": pid, "origen_id": esc.principal["id"], "destino_id": esc.camioneta["id"], "cantidad": 1})
        venta = esc.client.post("/api/ventas", json={
            "fecha": datetime.date.today().isoformat(),
            "items": [{"producto_id": pid, "nombre": esc.producto["nombre"], "qty": 1, "precio": 5000.0}],
            "pagos": [{"medio": "efectivo", "monto": 5000.0}],
        })
    for r in (ajuste, transferencia, venta):
        assert r.status_code == 409, r.text
        assert r.json()["codigo"] == "deposito_de_sucursal_con_nodo" and r.json()["node_id"] == NODO
    assert _stock_del_central(esc, pid) == antes
    assert _en_el_central(esc, "SELECT COUNT(*) FROM sales") == ventas_antes, "la venta rechazada no deja ni la cabecera"
    assert _en_el_central(esc, "SELECT COUNT(*) FROM stock_movements WHERE origen IS NULL AND quantity_delta = 5") == [(0,)]

    # Un nodo dado de baja ya no es dueño del stock de su sucursal.
    from libraedge.db.repository import NodeRepository

    from app.db_core import get_connection

    with esc.central():
        with get_connection() as conn:
            NodeRepository(conn).deactivate_node(NODO)
            conn.commit()
        assert _ajustar(esc.client, pid, modo="entrada", cantidad=5).status_code == 200
    assert _stock_del_central(esc, pid) == antes + 5


def test_la_carga_inicial_trae_las_existencias_del_central_sin_duplicar_una_venta_ya_subida(escenario, monkeypatch):
    """De punta a punta con el `CargaInicialWorker` real de LibraEdge, la ruta `GET /sync/v1/carga-inicial` del producto y
    `aplicar_carga_inicial` de LibraCommerce (lo que declara `LIBRAEDGE_CARGA_INICIAL`)."""
    from libraedge.db.repository import NodeRepository
    from libraedge.sync import carga_inicial as carga
    from libraedge.sync.esquema import version_de_alembic

    esc = escenario
    pid = esc.producto["id"]
    monkeypatch.setattr(carga, "urlopen", _cable(esc))
    worker = carga.CargaInicialWorker(
        NodeRepository(esc.node_conn), esc.node_conn, NODO,
        carga.HttpCargaInicialTransport(CENTRAL, NODO, esc.secreto, version_esquema=version_de_alembic(esc.node_conn)),
        "libracommerce.erp.offline_stock:aplicar_carga_inicial")

    # El nodo vendió 3 y todavía no subió: la carga espera (contaría la venta dos veces).
    esc.vender(qty=3)
    intento = worker.run_once()
    assert intento.estado == carga.ESPERA and "operaciones_pendientes" in intento.detalle
    assert _stock_en_el_nodo(esc, pid) == 47.0
    esc.subir()
    assert _stock_del_central(esc, pid) == 47.0

    # Mientras tanto al central le entraron 20 (antes de que el nodo fuera el dueño del stock de la sucursal).
    with esc.central():
        from libraedge.db.repository import NodeRepository as Repositorio

        from app.db_core import get_connection

        with get_connection() as conn:
            conn.execute("UPDATE node_identity SET active = 0")
            conn.commit()
        assert _ajustar(esc.client, pid, modo="entrada", cantidad=20).status_code == 200
        with get_connection() as conn:
            conn.execute("UPDATE node_identity SET active = 1")
            conn.commit()
            assert Repositorio(conn).verify_node_secret(NODO, esc.secreto)
    assert _stock_del_central(esc, pid) == 67.0

    intento = worker.run_once()
    assert intento.estado == carga.HECHA, intento
    assert intento.resultado["ajustes"] == 1, "sólo la diferencia (+20): lo vendido y ya subido está en las dos puntas"
    assert _stock_en_el_nodo(esc, pid) == 67.0
    assert _stock_del_central(esc, pid) == 67.0, "el central no se entera de nada: la carga no sube"
    assert _operaciones_sin_subir(esc) == []
    ajuste = [tuple(f) for f in esc.node_conn.execute(
        "SELECT quantity_delta, reason_code FROM stock_movements WHERE reason_code = 'carga_inicial'").fetchall()]
    esc.node_conn.commit()
    assert ajuste == [(20.0, "carga_inicial")]

    # Una vez por nodo, y volver a correrla a la fuerza (soporte) es idempotente: delta cero.
    assert worker.run_once().estado == carga.YA_HECHA
    forzada = worker.run_once(forzar=True)
    assert forzada.estado == carga.HECHA and forzada.resultado["ajustes"] == 0
    assert _stock_en_el_nodo(esc, pid) == 67.0


def test_la_carga_inicial_es_de_la_sucursal_del_nodo_autenticado(escenario):
    """La sucursal sale del nodo registrado y no del pedido; sin secreto del nodo, 401."""
    from libraedge.sync.esquema import cabeceras_del_nodo, version_de_alembic

    esc = escenario
    version = version_de_alembic(esc.node_conn)
    with esc.central():
        sin_secreto = esc.client.get("/sync/v1/carga-inicial", params={"node_id": NODO})
        r = esc.client.get("/sync/v1/carga-inicial", params={"node_id": NODO},
                           headers=cabeceras_del_nodo(esc.secreto, version))
    assert sin_secreto.status_code == 401
    assert r.status_code == 200, r.text
    datos = r.json()
    assert {d["nombre"] for d in datos["depositos"]} >= {"Camioneta"}
    assert [s["cantidad"] for s in datos["saldos"] if s["item_id"] == esc.producto["id"]] == ["50"]
