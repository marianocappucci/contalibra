import sqlite3
import json
import os
import hashlib
import secrets

_DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(__file__))
DB_PATH   = os.path.join(_DATA_DIR, "contalibra.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                address       TEXT,
                cuit_dni      TEXT,
                email         TEXT,
                phone         TEXT,
                iva_condition TEXT DEFAULT '',
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS remitos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                number         TEXT NOT NULL UNIQUE,
                date           TEXT NOT NULL,
                client_id      INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                client_name    TEXT NOT NULL,
                client_address TEXT,
                client_cuit    TEXT,
                client_email   TEXT,
                client_phone   TEXT,
                items          TEXT NOT NULL,
                subtotal       REAL NOT NULL,
                tax_rate       REAL NOT NULL DEFAULT 0.21,
                tax_amount     REAL NOT NULL,
                total          REAL NOT NULL,
                observations   TEXT,
                pdf_path       TEXT,
                created_at     TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS presupuestos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                number          TEXT NOT NULL UNIQUE,
                date            TEXT NOT NULL,
                valid_until     TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pendiente',
                client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                client_name     TEXT NOT NULL,
                client_address  TEXT,
                client_cuit     TEXT,
                client_email    TEXT,
                client_phone    TEXT,
                items           TEXT NOT NULL,
                subtotal        REAL NOT NULL,
                tax_rate        REAL NOT NULL DEFAULT 0.21,
                tax_amount      REAL NOT NULL,
                total           REAL NOT NULL,
                observations    TEXT,
                pdf_path        TEXT,
                remito_id       INTEGER REFERENCES remitos(id),
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS facturas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo            INTEGER NOT NULL,
                punto_venta     INTEGER NOT NULL,
                numero          INTEGER NOT NULL,
                fecha           TEXT NOT NULL,
                cliente_cuit    TEXT,
                cliente_razon   TEXT,
                cliente_iva_cond INTEGER,
                items           TEXT NOT NULL,
                subtotal        REAL NOT NULL,
                iva_amount      REAL NOT NULL,
                total           REAL NOT NULL,
                concepto        INTEGER NOT NULL DEFAULT 1,
                cae             TEXT,
                cae_vto         TEXT,
                observaciones   TEXT,
                pdf_path        TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS caja_movimientos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT NOT NULL,
                tipo        TEXT NOT NULL,
                concepto    TEXT NOT NULL,
                monto       REAL NOT NULL,
                referencia  TEXT DEFAULT '',
                factura_id  INTEGER,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS mp_pagos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                mp_payment_id   TEXT NOT NULL UNIQUE,
                status          TEXT,
                monto           REAL,
                payer_email     TEXT,
                payer_name      TEXT,
                factura_id      INTEGER,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS arca_config (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa         TEXT NOT NULL UNIQUE,
                cuit            TEXT NOT NULL,
                punto_venta     INTEGER NOT NULL,
                clave_path      TEXT NOT NULL,
                certificado_path TEXT NOT NULL,
                ambiente        TEXT DEFAULT 'homologacion',
                activo          INTEGER DEFAULT 1,
                alias           TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                nombre        TEXT NOT NULL,
                email         TEXT DEFAULT '',
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'operador',
                activo        INTEGER NOT NULL DEFAULT 1,
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS modulos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                modulo     TEXT NOT NULL UNIQUE,
                habilitado INTEGER NOT NULL DEFAULT 1,
                plan       TEXT NOT NULL DEFAULT 'estandar'
            );

            CREATE TABLE IF NOT EXISTS productos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo       TEXT UNIQUE,
                nombre       TEXT NOT NULL,
                descripcion  TEXT DEFAULT '',
                precio_venta REAL NOT NULL DEFAULT 0,
                precio_costo REAL NOT NULL DEFAULT 0,
                unidad       TEXT NOT NULL DEFAULT 'u',
                categoria    TEXT DEFAULT '',
                activo       INTEGER NOT NULL DEFAULT 1,
                created_at   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS turnos_caja (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id             INTEGER NOT NULL REFERENCES usuarios(id),
                apertura               TEXT NOT NULL,
                cierre                 TEXT,
                monto_inicial          REAL NOT NULL DEFAULT 0,
                monto_declarado_cierre REAL,
                monto_esperado_cierre  REAL,
                estado                 TEXT NOT NULL DEFAULT 'abierto',
                notas                  TEXT DEFAULT '',
                created_at             TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS movimientos_stock (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                tipo        TEXT NOT NULL,
                cantidad    REAL NOT NULL,
                referencia  TEXT DEFAULT '',
                venta_id    INTEGER REFERENCES ventas(id) ON DELETE SET NULL,
                usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                fecha       TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ventas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                numero          TEXT NOT NULL UNIQUE,
                fecha           TEXT NOT NULL,
                cliente_id      INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                cliente_nombre  TEXT DEFAULT '',
                items           TEXT NOT NULL,
                subtotal        REAL NOT NULL DEFAULT 0,
                descuento       REAL NOT NULL DEFAULT 0,
                total           REAL NOT NULL DEFAULT 0,
                estado          TEXT NOT NULL DEFAULT 'cobrada',
                factura_id      INTEGER REFERENCES facturas(id) ON DELETE SET NULL,
                remito_id       INTEGER REFERENCES remitos(id) ON DELETE SET NULL,
                usuario_id      INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                observaciones   TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ventas_pagos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id   INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
                medio      TEXT NOT NULL,
                monto      REAL NOT NULL,
                referencia TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        # Migración: columnas faltantes
        cols = [r[1] for r in conn.execute("PRAGMA table_info(clients)").fetchall()]
        if "iva_condition" not in cols:
            conn.execute("ALTER TABLE clients ADD COLUMN iva_condition TEXT DEFAULT ''")
        fact_cols = [r[1] for r in conn.execute("PRAGMA table_info(facturas)").fetchall()]
        if "cliente_domicilio" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN cliente_domicilio TEXT DEFAULT ''")
        if "fch_serv_desde" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN fch_serv_desde TEXT DEFAULT ''")
        if "fch_serv_hasta" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN fch_serv_hasta TEXT DEFAULT ''")
        if "fch_vto_pago" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN fch_vto_pago TEXT DEFAULT ''")
        if "cbte_asoc_tipo" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN cbte_asoc_tipo INTEGER DEFAULT 0")
        if "cbte_asoc_pv" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN cbte_asoc_pv INTEGER DEFAULT 0")
        if "cbte_asoc_nro" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN cbte_asoc_nro INTEGER DEFAULT 0")

        prod_cols = [r[1] for r in conn.execute("PRAGMA table_info(productos)").fetchall()]
        if "stock_minimo" not in prod_cols:
            conn.execute("ALTER TABLE productos ADD COLUMN stock_minimo REAL NOT NULL DEFAULT 0")
        ventas_cols = [r[1] for r in conn.execute("PRAGMA table_info(ventas)").fetchall()]
        if ventas_cols and "turno_id" not in ventas_cols:
            conn.execute("ALTER TABLE ventas ADD COLUMN turno_id INTEGER REFERENCES turnos_caja(id) ON DELETE SET NULL")
        if ventas_cols and "mp_order_id" not in ventas_cols:
            conn.execute("ALTER TABLE ventas ADD COLUMN mp_order_id TEXT DEFAULT ''")
        if ventas_cols and "mp_payment_id" not in ventas_cols:
            conn.execute("ALTER TABLE ventas ADD COLUMN mp_payment_id TEXT DEFAULT ''")

        # Seed de módulos: inserta sólo los que no existen aún
        _MODULOS_DEFAULT = [
            ("clientes",      1, "basico"),
            ("caja",          1, "basico"),
            ("ventas",        1, "basico"),
            ("facturacion",   1, "estandar"),
            ("remitos",       1, "estandar"),
            ("presupuestos",  1, "estandar"),
            ("productos",     1, "estandar"),
            ("stock",         1, "premium"),
            ("reportes",      1, "estandar"),
        ]
        for modulo, habilitado, plan in _MODULOS_DEFAULT:
            conn.execute(
                "INSERT OR IGNORE INTO modulos (modulo, habilitado, plan) VALUES (?,?,?)",
                (modulo, habilitado, plan),
            )


# ── Clients ────────────────────────────────────────────────────────────────────

def create_client(name, address="", cuit_dni="", email="", phone="", iva_condition=""):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO clients (name, address, cuit_dni, email, phone, iva_condition) VALUES (?,?,?,?,?,?)",
            (name, address, cuit_dni, email, phone, iva_condition),
        )
        return cur.lastrowid


def get_all_clients():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM clients ORDER BY name")]


def get_client(client_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        return dict(row) if row else None


def update_client(client_id, name=None, address=None, cuit_dni=None, email=None, phone=None, iva_condition=None):
    client = get_client(client_id)
    if not client:
        return
    with get_connection() as conn:
        conn.execute(
            """UPDATE clients SET name=?, address=?, cuit_dni=?, email=?, phone=?, iva_condition=?
               WHERE id=?""",
            (
                name          if name          is not None else client["name"],
                address       if address       is not None else client["address"],
                cuit_dni      if cuit_dni      is not None else client["cuit_dni"],
                email         if email         is not None else client["email"],
                phone         if phone         is not None else client["phone"],
                iva_condition if iva_condition is not None else client.get("iva_condition", ""),
                client_id,
            ),
        )


def delete_client(client_id):
    with get_connection() as conn:
        remito_count = conn.execute(
            "SELECT COUNT(*) FROM remitos WHERE client_id=?", (client_id,)
        ).fetchone()[0]
        presupuesto_count = conn.execute(
            "SELECT COUNT(*) FROM presupuestos WHERE client_id=?", (client_id,)
        ).fetchone()[0]
        total_count = remito_count + presupuesto_count
        if total_count > 0:
            msg_parts = []
            if remito_count > 0:
                msg_parts.append(f"{remito_count} remito(s)")
            if presupuesto_count > 0:
                msg_parts.append(f"{presupuesto_count} presupuesto(s)")
            raise ValueError(f"El cliente tiene {' y '.join(msg_parts)} asociado(s) y no puede eliminarse.")
        conn.execute("DELETE FROM clients WHERE id=?", (client_id,))


# ── Remitos ────────────────────────────────────────────────────────────────────

def get_next_remito_number():
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(id) FROM remitos").fetchone()
        next_id = (row[0] or 0) + 1
        return f"0001-{next_id:08d}"


def create_remito(number, date, client_id, client_name, client_address, client_cuit,
                  client_email, client_phone, items, subtotal, tax_rate, tax_amount,
                  total, observations="", pdf_path=""):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO remitos
               (number, date, client_id, client_name, client_address, client_cuit,
                client_email, client_phone, items, subtotal, tax_rate, tax_amount,
                total, observations, pdf_path)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                number, date, client_id, client_name, client_address, client_cuit,
                client_email, client_phone, json.dumps(items, ensure_ascii=False),
                subtotal, tax_rate, tax_amount, total, observations, pdf_path,
            ),
        )
        return cur.lastrowid


def update_remito_pdf_path(remito_id, pdf_path):
    with get_connection() as conn:
        conn.execute("UPDATE remitos SET pdf_path=? WHERE id=?", (pdf_path, remito_id))


def get_all_remitos(limit=100):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM remitos ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def get_remito(remito_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM remitos WHERE id=?", (remito_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        return d


def get_remitos_by_client(client_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM remitos WHERE client_id=? ORDER BY id DESC", (client_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def search_remitos(query):
    q = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM remitos
               WHERE number LIKE ? OR client_name LIKE ? OR observations LIKE ?
               ORDER BY id DESC""",
            (q, q, q),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


# ── Presupuestos ───────────────────────────────────────────────────────────────

def get_next_presupuesto_number():
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(id) FROM presupuestos").fetchone()
        next_id = (row[0] or 0) + 1
        return f"PRES-{next_id:08d}"


def create_presupuesto(number, date, valid_until, client_id, client_name, client_address,
                       client_cuit, client_email, client_phone, items, subtotal, tax_rate,
                       tax_amount, total, observations="", pdf_path="", status="pendiente"):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO presupuestos
               (number, date, valid_until, status, client_id, client_name, client_address,
                client_cuit, client_email, client_phone, items, subtotal, tax_rate,
                tax_amount, total, observations, pdf_path)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                number, date, valid_until, status, client_id, client_name, client_address,
                client_cuit, client_email, client_phone, json.dumps(items, ensure_ascii=False),
                subtotal, tax_rate, tax_amount, total, observations, pdf_path,
            ),
        )
        return cur.lastrowid


def update_presupuesto_pdf_path(presupuesto_id, pdf_path):
    with get_connection() as conn:
        conn.execute("UPDATE presupuestos SET pdf_path=? WHERE id=?", (pdf_path, presupuesto_id))


def update_presupuesto_status(presupuesto_id, status):
    with get_connection() as conn:
        conn.execute("UPDATE presupuestos SET status=? WHERE id=?", (status, presupuesto_id))


def update_presupuesto_remito_id(presupuesto_id, remito_id):
    with get_connection() as conn:
        conn.execute("UPDATE presupuestos SET remito_id=? WHERE id=?", (remito_id, presupuesto_id))


def get_all_presupuestos(limit=100):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM presupuestos ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def get_presupuesto(presupuesto_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM presupuestos WHERE id=?", (presupuesto_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        return d


def get_presupuestos_by_client(client_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM presupuestos WHERE client_id=? ORDER BY id DESC", (client_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def search_presupuestos(query):
    q = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM presupuestos
               WHERE number LIKE ? OR client_name LIKE ? OR observations LIKE ?
               ORDER BY id DESC""",
            (q, q, q),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


# ── Eliminar ───────────────────────────────────────────────────────────────────

def delete_remito(remito_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM remitos WHERE id=?", (remito_id,))


def delete_presupuesto(presupuesto_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM presupuestos WHERE id=?", (presupuesto_id,))


# ── Actualizar ──────────────────────────────────────────────────────────────────

def update_remito(remito_id, date, client_id, client_name, client_address, client_cuit,
                  client_email, client_phone, items, subtotal, tax_rate, tax_amount,
                  total, observations=""):
    with get_connection() as conn:
        conn.execute(
            """UPDATE remitos
               SET date=?, client_id=?, client_name=?, client_address=?, client_cuit=?,
                   client_email=?, client_phone=?, items=?, subtotal=?, tax_rate=?,
                   tax_amount=?, total=?, observations=?
               WHERE id=?""",
            (
                date, client_id, client_name, client_address, client_cuit,
                client_email, client_phone, json.dumps(items, ensure_ascii=False),
                subtotal, tax_rate, tax_amount, total, observations, remito_id,
            ),
        )


def update_presupuesto(presupuesto_id, date, valid_until, status, client_id, client_name,
                       client_address, client_cuit, client_email, client_phone, items,
                       subtotal, tax_rate, tax_amount, total, observations=""):
    with get_connection() as conn:
        conn.execute(
            """UPDATE presupuestos
               SET date=?, valid_until=?, status=?, client_id=?, client_name=?,
                   client_address=?, client_cuit=?, client_email=?, client_phone=?,
                   items=?, subtotal=?, tax_rate=?, tax_amount=?, total=?, observations=?
               WHERE id=?""",
            (
                date, valid_until, status, client_id, client_name, client_address,
                client_cuit, client_email, client_phone, json.dumps(items, ensure_ascii=False),
                subtotal, tax_rate, tax_amount, total, observations, presupuesto_id,
            ),
        )


# ── Configuración ARCA ──────────────────────────────────────────────────────────

def crear_arca_config(empresa, cuit, punto_venta, clave_path, certificado_path,
                      ambiente="homologacion", alias=""):
    """Crea configuración ARCA para una empresa."""
    with get_connection() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO arca_config
                   (empresa, cuit, punto_venta, clave_path, certificado_path, ambiente, alias)
                   VALUES (?,?,?,?,?,?,?)""",
                (empresa, cuit, punto_venta, clave_path, certificado_path, ambiente, alias),
            )
            return cur.lastrowid
        except Exception as e:
            raise ValueError(f"Error creando configuración ARCA: {str(e)}")


def obtener_arca_config(empresa):
    """Obtiene configuración ARCA por nombre de empresa."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM arca_config WHERE empresa=? AND activo=1", (empresa,)
        ).fetchone()
        return dict(row) if row else None


def obtener_todas_arca_configs():
    """Obtiene todas las configuraciones ARCA activas."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM arca_config WHERE activo=1 ORDER BY empresa"
        ).fetchall()
        return [dict(r) for r in rows]


def actualizar_arca_config(empresa, cuit=None, punto_venta=None, clave_path=None,
                          certificado_path=None, ambiente=None, alias=None):
    """Actualiza configuración ARCA."""
    with get_connection() as conn:
        config = obtener_arca_config(empresa)
        if not config:
            raise ValueError(f"Configuración ARCA no encontrada para: {empresa}")

        conn.execute(
            """UPDATE arca_config
               SET cuit=?, punto_venta=?, clave_path=?, certificado_path=?,
                   ambiente=?, alias=?, updated_at=datetime('now')
               WHERE empresa=?""",
            (
                cuit if cuit is not None else config["cuit"],
                punto_venta if punto_venta is not None else config["punto_venta"],
                clave_path if clave_path is not None else config["clave_path"],
                certificado_path if certificado_path is not None else config["certificado_path"],
                ambiente if ambiente is not None else config["ambiente"],
                alias if alias is not None else config["alias"],
                empresa,
            ),
        )


def eliminar_arca_config(empresa):
    """Marca como inactivo la configuración ARCA."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE arca_config SET activo=0 WHERE empresa=?", (empresa,)
        )


# ── Facturas ────────────────────────────────────────────────────────────────────

def get_next_factura_numero(punto_venta, tipo):
    """Devuelve el próximo número correlativo para tipo+punto_venta."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(numero) FROM facturas WHERE punto_venta=? AND tipo=?",
            (punto_venta, tipo),
        ).fetchone()
        return (row[0] or 0) + 1


def create_factura(tipo, punto_venta, numero, fecha, cliente_cuit, cliente_razon,
                   cliente_iva_cond, items, subtotal, iva_amount, total,
                   concepto=1, cae="", cae_vto="", observaciones="", pdf_path="",
                   cliente_domicilio="", fch_serv_desde="", fch_serv_hasta="",
                   fch_vto_pago="", cbte_asoc_tipo=0, cbte_asoc_pv=0, cbte_asoc_nro=0):
    """Crea una nueva factura electrónica."""
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO facturas
               (tipo, punto_venta, numero, fecha, cliente_cuit, cliente_razon,
                cliente_iva_cond, items, subtotal, iva_amount, total, concepto,
                cae, cae_vto, observaciones, pdf_path, cliente_domicilio,
                fch_serv_desde, fch_serv_hasta, fch_vto_pago,
                cbte_asoc_tipo, cbte_asoc_pv, cbte_asoc_nro)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tipo, punto_venta, numero, fecha, cliente_cuit, cliente_razon,
             cliente_iva_cond, json.dumps(items, ensure_ascii=False), subtotal,
             iva_amount, total, concepto, cae, cae_vto, observaciones, pdf_path,
             cliente_domicilio, fch_serv_desde, fch_serv_hasta, fch_vto_pago,
             cbte_asoc_tipo, cbte_asoc_pv, cbte_asoc_nro),
        )
        return cur.lastrowid


_TIPOS_FACTURA = (1, 6, 11)
_TIPOS_NC      = (3, 8, 13)
_TIPOS_ND      = (2, 7, 12)

_VISTA_TIPOS = {
    "facturas": _TIPOS_FACTURA,
    "nc":       _TIPOS_NC,
    "nd":       _TIPOS_ND,
}


def get_all_facturas(limit=100, vista="facturas"):
    """Obtiene facturas, notas de crédito o notas de débito (últimas primero)."""
    tipos = _VISTA_TIPOS.get(vista, _TIPOS_FACTURA)
    placeholders = ",".join("?" * len(tipos))
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM facturas WHERE tipo IN ({placeholders}) ORDER BY id DESC LIMIT ?",
            (*tipos, limit),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def get_facturas_filtradas(desde="", hasta="", q="", vista="facturas", limit=50, offset=0):
    """Listado de facturas con filtros de fecha, búsqueda y paginación."""
    solo_sin_cobrar = (vista == "sin_cobrar")
    tipos = _VISTA_TIPOS.get("facturas" if solo_sin_cobrar else vista, _TIPOS_FACTURA)
    ph = ",".join("?" * len(tipos))
    conds = [f"f.tipo IN ({ph})"]
    params = list(tipos)
    if desde:
        conds.append("f.fecha >= ?"); params.append(desde)
    if hasta:
        conds.append("f.fecha <= ?"); params.append(hasta)
    if q:
        conds.append("(CAST(f.numero AS TEXT) LIKE ? OR f.cliente_razon LIKE ? OR f.observaciones LIKE ?)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if solo_sin_cobrar:
        conds.append("f.cae != '' AND f.cae IS NOT NULL AND f.cae != 'PENDIENTE'")
        conds.append("NOT EXISTS(SELECT 1 FROM caja_movimientos cm WHERE cm.factura_id=f.id AND cm.tipo='ingreso')")
    where = " AND ".join(conds)
    cobrada_col = "EXISTS(SELECT 1 FROM caja_movimientos cm WHERE cm.factura_id=f.id AND cm.tipo='ingreso') AS cobrada"
    with get_connection() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM facturas f WHERE {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT f.*, {cobrada_col} FROM facturas f WHERE {where} ORDER BY f.id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["items"] = json.loads(d["items"])
        result.append(d)
    return {"items": result, "total": total}


def get_factura(factura_id):
    """Obtiene una factura por ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM facturas WHERE id=?", (factura_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        return d


def update_factura_cae(factura_id, cae, cae_vto):
    """Actualiza CAE de una factura después de obtenerlo de ARCA."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE facturas SET cae=?, cae_vto=? WHERE id=?",
            (cae, cae_vto, factura_id)
        )


def update_factura_pdf_path(factura_id, pdf_path):
    """Actualiza el path del PDF de la factura."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE facturas SET pdf_path=? WHERE id=?",
            (pdf_path, factura_id)
        )


def search_facturas(query, vista="facturas"):
    """Busca facturas por número, cliente u observaciones."""
    tipos = _VISTA_TIPOS.get(vista, _TIPOS_FACTURA)
    placeholders = ",".join("?" * len(tipos))
    q = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT * FROM facturas
               WHERE tipo IN ({placeholders})
                 AND (numero LIKE ? OR cliente_razon LIKE ? OR observaciones LIKE ?)
               ORDER BY id DESC""",
            (*tipos, q, q, q),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def get_notas_de_factura(tipo, punto_venta, numero, tipos_nota):
    """Devuelve notas (NC o ND) que referencian un comprobante."""
    placeholders = ",".join("?" * len(tipos_nota))
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT * FROM facturas
               WHERE tipo IN ({placeholders})
                 AND cbte_asoc_tipo=? AND cbte_asoc_pv=? AND cbte_asoc_nro=?
               ORDER BY id DESC""",
            (*tipos_nota, tipo, punto_venta, numero),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def get_nc_de_factura(tipo, punto_venta, numero):
    """Devuelve las notas de crédito que anulan un comprobante."""
    return get_notas_de_factura(tipo, punto_venta, numero, _TIPOS_NC)


def get_nd_de_factura(tipo, punto_venta, numero):
    """Devuelve las notas de débito asociadas a un comprobante."""
    return get_notas_de_factura(tipo, punto_venta, numero, _TIPOS_ND)


def get_factura_por_tipo_pv_nro(tipo, punto_venta, numero):
    """Busca un comprobante por tipo + punto de venta + número."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM facturas WHERE tipo=? AND punto_venta=? AND numero=?",
            (tipo, punto_venta, numero),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        return d


def delete_factura(factura_id):
    """Elimina una factura."""
    with get_connection() as conn:
        conn.execute("DELETE FROM facturas WHERE id=?", (factura_id,))


# ── Caja ───────────────────────────────────────────────────────────────────────

def create_caja_movimiento(fecha, tipo, concepto, monto, referencia="", factura_id=None):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO caja_movimientos (fecha, tipo, concepto, monto, referencia, factura_id)
               VALUES (?,?,?,?,?,?)""",
            (fecha, tipo, concepto, float(monto), referencia, factura_id),
        )
        return cur.lastrowid


def get_caja_movimientos(desde=None, hasta=None, limit=500):
    with get_connection() as conn:
        if desde and hasta:
            rows = conn.execute(
                "SELECT * FROM caja_movimientos WHERE fecha BETWEEN ? AND ? ORDER BY fecha DESC, id DESC LIMIT ?",
                (desde, hasta, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM caja_movimientos ORDER BY fecha DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_caja_resumen(desde=None, hasta=None):
    """Devuelve {ingresos, egresos, saldo_periodo, saldo_total}."""
    with get_connection() as conn:
        if desde and hasta:
            row = conn.execute(
                """SELECT
                     COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE 0 END), 0) AS ingresos,
                     COALESCE(SUM(CASE WHEN tipo='egreso'  THEN monto ELSE 0 END), 0) AS egresos
                   FROM caja_movimientos WHERE fecha BETWEEN ? AND ?""",
                (desde, hasta),
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT
                     COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE 0 END), 0) AS ingresos,
                     COALESCE(SUM(CASE WHEN tipo='egreso'  THEN monto ELSE 0 END), 0) AS egresos
                   FROM caja_movimientos""",
            ).fetchone()
        ingresos = row["ingresos"]
        egresos  = row["egresos"]

        total = conn.execute(
            """SELECT COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END), 0)
               FROM caja_movimientos"""
        ).fetchone()[0]

        return {
            "ingresos":     ingresos,
            "egresos":      egresos,
            "saldo_periodo": ingresos - egresos,
            "saldo_total":  total,
        }


def get_cobro_factura(factura_id):
    """Devuelve el movimiento de cobro de una factura, o None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM caja_movimientos WHERE factura_id=? AND tipo='ingreso' ORDER BY id DESC LIMIT 1",
            (factura_id,),
        ).fetchone()
        return dict(row) if row else None


def delete_caja_movimiento(mov_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM caja_movimientos WHERE id=?", (mov_id,))


# ── MercadoPago pagos ──────────────────────────────────────────────────────────

def get_mp_pago(mp_payment_id: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM mp_pagos WHERE mp_payment_id=?", (str(mp_payment_id),)
        ).fetchone()
        return dict(row) if row else None


def create_mp_pago(mp_payment_id: str, status: str, monto: float,
                   payer_email: str, payer_name: str, factura_id=None):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO mp_pagos (mp_payment_id, status, monto, payer_email, payer_name, factura_id)
               VALUES (?,?,?,?,?,?)""",
            (str(mp_payment_id), status, float(monto), payer_email, payer_name, factura_id),
        )
        return cur.lastrowid


def get_client_by_email(email: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE email=? LIMIT 1", (email,)
        ).fetchone()
        return dict(row) if row else None


# ── Dashboard ──────────────────────────────────────────────────────────────────

def get_dashboard_data(mes_desde: str, mes_hasta: str) -> dict:
    """Devuelve todos los datos necesarios para el dashboard en una sola llamada."""
    _TIPOS_FACTURA = (1, 6, 11)
    with get_connection() as conn:
        # KPI 1: total facturado en el mes (solo facturas, no NC/ND)
        row = conn.execute(
            "SELECT COALESCE(SUM(total), 0) FROM facturas WHERE tipo IN (1,6,11) AND fecha BETWEEN ? AND ?",
            (mes_desde, mes_hasta),
        ).fetchone()
        facturado_mes = row[0]

        # KPI 2/3: ingresos y egresos de caja del mes
        row = conn.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE 0 END), 0),
                 COALESCE(SUM(CASE WHEN tipo='egreso'  THEN monto ELSE 0 END), 0)
               FROM caja_movimientos WHERE fecha BETWEEN ? AND ?""",
            (mes_desde, mes_hasta),
        ).fetchone()
        cobrado_mes = row[0]
        egresos_mes = row[1]

        # KPI 4: saldo total de caja (histórico)
        saldo_total = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END), 0) FROM caja_movimientos"
        ).fetchone()[0]

        # Cantidad de facturas emitidas en el mes
        cant_facturas_mes = conn.execute(
            "SELECT COUNT(*) FROM facturas WHERE tipo IN (1,6,11) AND fecha BETWEEN ? AND ?",
            (mes_desde, mes_hasta),
        ).fetchone()[0]

        # Facturas sin cobrar (tipo factura, sin ingreso en caja)
        rows = conn.execute(
            """SELECT f.id, f.tipo, f.punto_venta, f.numero, f.fecha, f.cliente_razon, f.total
               FROM facturas f
               LEFT JOIN caja_movimientos c ON c.factura_id = f.id AND c.tipo = 'ingreso'
               WHERE f.tipo IN (1,6,11) AND c.id IS NULL
               ORDER BY f.id DESC LIMIT 8""",
        ).fetchall()
        facturas_sin_cobrar = [dict(r) for r in rows]

        # Presupuestos pendientes de respuesta
        rows = conn.execute(
            "SELECT id, number, date, client_name, total FROM presupuestos WHERE status='pendiente' ORDER BY id DESC LIMIT 8"
        ).fetchall()
        presupuestos_pendientes = [dict(r) for r in rows]

        # Últimos 6 movimientos de caja
        rows = conn.execute(
            "SELECT * FROM caja_movimientos ORDER BY fecha DESC, id DESC LIMIT 6"
        ).fetchall()
        ultimos_movimientos = [dict(r) for r in rows]

    return {
        "facturado_mes":        facturado_mes,
        "cobrado_mes":          cobrado_mes,
        "egresos_mes":          egresos_mes,
        "saldo_total":          saldo_total,
        "cant_facturas_mes":    cant_facturas_mes,
        "facturas_sin_cobrar":  facturas_sin_cobrar,
        "presupuestos_pendientes": presupuestos_pendientes,
        "ultimos_movimientos":  ultimos_movimientos,
    }


# ── Usuarios ──────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(32)
    dk   = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"pbkdf2:sha256:{salt}:{dk.hex()}"


def _verify_password(stored: str, provided: str) -> bool:
    try:
        _, algo, salt, stored_hash = stored.split(":")
        dk = hashlib.pbkdf2_hmac(algo, provided.encode(), salt.encode(), 260_000)
        return dk.hex() == stored_hash
    except Exception:
        return False


def create_usuario(username: str, nombre: str, email: str,
                   password: str, role: str = "operador") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO usuarios (username, nombre, email, password_hash, role) VALUES (?,?,?,?,?)",
            (username.strip(), nombre.strip(), email.strip(),
             _hash_password(password), role),
        )
        return cur.lastrowid


def get_usuario_by_username(username: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE username=? AND activo=1", (username,)
        ).fetchone()
        return dict(row) if row else None


def get_usuario_by_id(uid: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()
        return dict(row) if row else None


def get_all_usuarios() -> list:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM usuarios ORDER BY role DESC, username"
        ).fetchall()]


def update_usuario(uid: int, nombre: str, email: str, role: str, activo: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET nombre=?, email=?, role=?, activo=? WHERE id=?",
            (nombre.strip(), email.strip(), role, activo, uid),
        )


def update_usuario_password(uid: int, new_password: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET password_hash=? WHERE id=?",
            (_hash_password(new_password), uid),
        )


def delete_usuario(uid: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM usuarios WHERE id=?", (uid,))


def check_usuario_credentials(username: str, password: str) -> dict | None:
    """Devuelve el usuario si las credenciales son válidas, None si no."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE username=? AND activo=1", (username,)
        ).fetchone()
    if not row:
        return None
    user = dict(row)
    return user if _verify_password(user["password_hash"], password) else None


def ensure_admin_user():
    """Crea el usuario admin por defecto si no existe ningún usuario."""
    if get_all_usuarios():
        return
    username = os.environ.get("ADMIN_USER", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")
    nombre   = os.environ.get("ADMIN_NOMBRE", "Administrador")
    if not password:
        password = secrets.token_urlsafe(12)
        print(f"[WARN] ADMIN_PASSWORD no configurado. Contraseña generada: {password}")
    create_usuario(username=username, nombre=nombre, email="", password=password, role="admin")
    print(f"[INFO] Usuario admin '{username}' creado.")


# ── Productos ─────────────────────────────────────────────────────────────────

def create_producto(nombre: str, codigo: str = "", descripcion: str = "",
                    precio_venta: float = 0, precio_costo: float = 0,
                    unidad: str = "u", categoria: str = "",
                    stock_minimo: float = 0) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO productos
               (codigo, nombre, descripcion, precio_venta, precio_costo,
                unidad, categoria, stock_minimo)
               VALUES (?,?,?,?,?,?,?,?)""",
            (codigo or None, nombre, descripcion, precio_venta, precio_costo,
             unidad, categoria, stock_minimo),
        )
        return cur.lastrowid


def get_all_productos(solo_activos: bool = False, q: str = "") -> list[dict]:
    with get_connection() as conn:
        where = []
        params = []
        if solo_activos:
            where.append("activo=1")
        if q:
            where.append("(nombre LIKE ? OR codigo LIKE ? OR categoria LIKE ?)")
            params += [f"%{q}%", f"%{q}%", f"%{q}%"]
        sql = "SELECT * FROM productos"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY nombre"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_producto(pid: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else None


def get_producto_by_codigo(codigo: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM productos WHERE codigo=? AND activo=1", (codigo,)
        ).fetchone()
        return dict(row) if row else None


def update_producto(pid: int, nombre: str, codigo: str, descripcion: str,
                    precio_venta: float, precio_costo: float,
                    unidad: str, categoria: str, activo: int,
                    stock_minimo: float = 0):
    with get_connection() as conn:
        conn.execute(
            """UPDATE productos SET nombre=?, codigo=?, descripcion=?,
               precio_venta=?, precio_costo=?, unidad=?, categoria=?,
               activo=?, stock_minimo=?
               WHERE id=?""",
            (nombre, codigo or None, descripcion, precio_venta, precio_costo,
             unidad, categoria, activo, stock_minimo, pid),
        )


def delete_producto(pid: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM productos WHERE id=?", (pid,))


# ── Turnos de caja ────────────────────────────────────────────────────────────

def create_turno(usuario_id: int, monto_inicial: float, notas: str = "") -> int:
    from datetime import datetime as _dt
    apertura = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO turnos_caja (usuario_id, apertura, monto_inicial, notas)
               VALUES (?,?,?,?)""",
            (usuario_id, apertura, monto_inicial, notas),
        )
        return cur.lastrowid


def get_turno_activo(usuario_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT t.*, u.nombre AS usuario_nombre
               FROM turnos_caja t JOIN usuarios u ON u.id = t.usuario_id
               WHERE t.usuario_id=? AND t.estado='abierto'
               ORDER BY t.id DESC LIMIT 1""",
            (usuario_id,),
        ).fetchone()
    return dict(row) if row else None


def get_turno_activo_any() -> dict | None:
    """Devuelve el primer turno abierto (para cajero sin usuario_id explícito)."""
    with get_connection() as conn:
        row = conn.execute(
            """SELECT t.*, u.nombre AS usuario_nombre
               FROM turnos_caja t JOIN usuarios u ON u.id = t.usuario_id
               WHERE t.estado='abierto' ORDER BY t.id DESC LIMIT 1"""
        ).fetchone()
    return dict(row) if row else None


def get_all_turnos(usuario_id: int | None = None, limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        if usuario_id:
            rows = conn.execute(
                """SELECT t.*, u.nombre AS usuario_nombre
                   FROM turnos_caja t JOIN usuarios u ON u.id = t.usuario_id
                   WHERE t.usuario_id=? ORDER BY t.id DESC LIMIT ?""",
                (usuario_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT t.*, u.nombre AS usuario_nombre
                   FROM turnos_caja t JOIN usuarios u ON u.id = t.usuario_id
                   ORDER BY t.id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_turno(tid: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT t.*, u.nombre AS usuario_nombre
               FROM turnos_caja t JOIN usuarios u ON u.id = t.usuario_id
               WHERE t.id=?""",
            (tid,),
        ).fetchone()
    return dict(row) if row else None


def get_resumen_turno(tid: int) -> dict:
    """Devuelve ventas y totales por medio de pago del turno."""
    with get_connection() as conn:
        ventas = conn.execute(
            """SELECT v.id, v.numero, v.fecha, v.cliente_nombre, v.total, v.estado
               FROM ventas v WHERE v.turno_id=? ORDER BY v.id""",
            (tid,),
        ).fetchall()
        pagos = conn.execute(
            """SELECT vp.medio, SUM(vp.monto) AS total
               FROM ventas_pagos vp
               JOIN ventas v ON v.id = vp.venta_id
               WHERE v.turno_id=? AND v.estado='cobrada'
               GROUP BY vp.medio""",
            (tid,),
        ).fetchall()
    return {
        "ventas": [dict(v) for v in ventas],
        "pagos_por_medio": {r["medio"]: r["total"] for r in pagos},
        "total_ventas": sum(r["total"] for r in pagos),
        "efectivo_ventas": next((r["total"] for r in pagos if r["medio"] == "efectivo"), 0.0),
    }


def cerrar_turno(tid: int, monto_declarado: float, notas: str = ""):
    from datetime import datetime as _dt
    turno = get_turno(tid)
    if not turno:
        return
    resumen = get_resumen_turno(tid)
    monto_esperado = round(turno["monto_inicial"] + resumen["efectivo_ventas"], 2)
    cierre = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            """UPDATE turnos_caja
               SET estado='cerrado', cierre=?, monto_declarado_cierre=?,
                   monto_esperado_cierre=?, notas=?
               WHERE id=?""",
            (cierre, monto_declarado, monto_esperado, notas, tid),
        )


def vincular_venta_turno(venta_id: int, turno_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE ventas SET turno_id=? WHERE id=?", (turno_id, venta_id))


# ── Stock ─────────────────────────────────────────────────────────────────────

def add_movimiento_stock(producto_id: int, tipo: str, cantidad: float,
                         referencia: str = "", fecha: str = "",
                         venta_id: int | None = None,
                         usuario_id: int | None = None):
    """Agrega un movimiento de stock. cantidad positiva=entrada, negativa=salida."""
    from datetime import date as _date
    _fecha = fecha or _date.today().isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO movimientos_stock
               (producto_id, tipo, cantidad, referencia, venta_id, usuario_id, fecha)
               VALUES (?,?,?,?,?,?,?)""",
            (producto_id, tipo, cantidad, referencia, venta_id, usuario_id, _fecha),
        )


def get_stock_actual(producto_id: int) -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(cantidad),0) FROM movimientos_stock WHERE producto_id=?",
            (producto_id,),
        ).fetchone()
    return float(row[0])


def get_stock_todos() -> list[dict]:
    """Devuelve todos los productos con su stock actual."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT p.id, p.codigo, p.nombre, p.unidad, p.categoria,
                   p.stock_minimo, p.activo,
                   COALESCE(SUM(m.cantidad), 0) AS stock_actual
            FROM productos p
            LEFT JOIN movimientos_stock m ON m.producto_id = p.id
            WHERE p.activo = 1
            GROUP BY p.id
            ORDER BY p.nombre
        """).fetchall()
    return [dict(r) for r in rows]


def get_movimientos_stock(producto_id: int | None = None,
                          desde: str = "", hasta: str = "",
                          limit: int = 200) -> list[dict]:
    with get_connection() as conn:
        where, params = [], []
        if producto_id:
            where.append("m.producto_id = ?"); params.append(producto_id)
        if desde:
            where.append("m.fecha >= ?"); params.append(desde)
        if hasta:
            where.append("m.fecha <= ?"); params.append(hasta)
        sql = """SELECT m.*, p.nombre AS producto_nombre, p.unidad
                 FROM movimientos_stock m
                 JOIN productos p ON p.id = m.producto_id"""
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY m.fecha DESC, m.id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def ajustar_stock(producto_id: int, stock_nuevo: float, referencia: str,
                  usuario_id: int | None = None, fecha: str = ""):
    """Crea un movimiento de ajuste para llevar el stock al valor indicado."""
    actual = get_stock_actual(producto_id)
    delta  = round(stock_nuevo - actual, 4)
    if delta == 0:
        return
    add_movimiento_stock(
        producto_id=producto_id, tipo="ajuste",
        cantidad=delta, referencia=referencia,
        usuario_id=usuario_id, fecha=fecha,
    )


def descontar_stock_venta(venta_id: int, items: list, fecha: str = "",
                           usuario_id: int | None = None):
    """Descuenta stock por cada ítem de la venta que tenga producto_id."""
    for item in items:
        pid = item.get("producto_id")
        if not pid:
            continue
        add_movimiento_stock(
            producto_id=pid, tipo="venta",
            cantidad=-abs(float(item.get("qty", 0))),
            referencia=f"Venta ID {venta_id}",
            venta_id=venta_id, usuario_id=usuario_id, fecha=fecha,
        )


# ── Ventas ────────────────────────────────────────────────────────────────────

def get_next_venta_numero() -> str:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT numero FROM ventas ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row:
        try:
            n = int(row["numero"].split("-")[-1]) + 1
        except (ValueError, IndexError):
            n = 1
    else:
        n = 1
    return f"V-{n:05d}"


def create_venta(numero: str, fecha: str, items: list, subtotal: float,
                 descuento: float, total: float, cliente_id: int | None,
                 cliente_nombre: str, usuario_id: int | None,
                 observaciones: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO ventas
               (numero, fecha, items, subtotal, descuento, total,
                cliente_id, cliente_nombre, usuario_id, observaciones)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (numero, fecha, json.dumps(items, ensure_ascii=False),
             subtotal, descuento, total,
             cliente_id, cliente_nombre, usuario_id, observaciones),
        )
        return cur.lastrowid


def add_venta_pago(venta_id: int, medio: str, monto: float, referencia: str = ""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO ventas_pagos (venta_id, medio, monto, referencia) VALUES (?,?,?,?)",
            (venta_id, medio, monto, referencia),
        )


def get_all_ventas(desde: str = "", hasta: str = "", q: str = "",
                   limit: int = 100, offset: int = 0) -> list[dict]:
    with get_connection() as conn:
        where, params = [], []
        if desde:
            where.append("v.fecha >= ?"); params.append(desde)
        if hasta:
            where.append("v.fecha <= ?"); params.append(hasta)
        if q:
            where.append("(v.numero LIKE ? OR v.cliente_nombre LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        sql = """SELECT v.*, GROUP_CONCAT(p.medio || ':' || p.monto, '|') AS pagos_raw
                 FROM ventas v
                 LEFT JOIN ventas_pagos p ON p.venta_id = v.id"""
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " GROUP BY v.id ORDER BY v.fecha DESC, v.id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = conn.execute(sql, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["items"] = json.loads(d["items"])
        d["pagos"] = _parse_pagos_raw(d.pop("pagos_raw", "") or "")
        result.append(d)
    return result


def get_venta(vid: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM ventas WHERE id=?", (vid,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        pagos = conn.execute(
            "SELECT * FROM ventas_pagos WHERE venta_id=? ORDER BY id", (vid,)
        ).fetchall()
        d["pagos"] = [dict(p) for p in pagos]
    return d


def _parse_pagos_raw(raw: str) -> list[dict]:
    pagos = []
    for part in raw.split("|"):
        if ":" in part:
            medio, monto = part.split(":", 1)
            try:
                pagos.append({"medio": medio, "monto": float(monto)})
            except ValueError:
                pass
    return pagos


def anular_venta(vid: int):
    with get_connection() as conn:
        conn.execute("UPDATE ventas SET estado='anulada' WHERE id=?", (vid,))


def vincular_venta_factura(vid: int, factura_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE ventas SET factura_id=? WHERE id=?", (factura_id, vid))


def vincular_venta_remito(vid: int, remito_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE ventas SET remito_id=? WHERE id=?", (remito_id, vid))


# ── Log de actividad ──────────────────────────────────────────────────────────

_LOG_TIPOS = ("venta", "caja", "stock", "factura", "turno", "remito", "presupuesto")

def get_actividad_log(tipos=None, usuario_id=None, turno_id=None,
                      desde="", hasta="", limit=200, offset=0) -> list[dict]:
    """
    Devuelve una línea de tiempo unificada de todos los movimientos del sistema.
    Cada fila: {fecha, tipo, descripcion, monto, usuario, turno_id, ref_id, ref_tabla}
    """
    partes = []

    # — Ventas —
    partes.append("""
        SELECT
            v.created_at AS ts,
            v.fecha,
            'venta'       AS tipo,
            'Venta ' || v.numero ||
              CASE WHEN v.cliente_nombre != '' THEN ' — ' || v.cliente_nombre ELSE '' END
              || ' (' || v.estado || ')'  AS descripcion,
            v.total       AS monto,
            COALESCE(u.nombre, '')        AS usuario,
            v.turno_id,
            v.id          AS ref_id,
            'ventas'      AS ref_tabla
        FROM ventas v
        LEFT JOIN usuarios u ON u.id = v.usuario_id
    """)

    # — Caja —
    partes.append("""
        SELECT
            cm.created_at AS ts,
            cm.fecha,
            'caja'        AS tipo,
            cm.tipo || ': ' || cm.concepto AS descripcion,
            cm.monto      AS monto,
            ''            AS usuario,
            NULL          AS turno_id,
            cm.id         AS ref_id,
            'caja_movimientos' AS ref_tabla
        FROM caja_movimientos cm
    """)

    # — Stock —
    partes.append("""
        SELECT
            ms.created_at AS ts,
            ms.fecha,
            'stock'       AS tipo,
            ms.tipo || ' ' || p.nombre ||
              ' (' || CAST(ms.cantidad AS TEXT) || ' ' || p.unidad || ')'
              || CASE WHEN ms.referencia != '' THEN ' — ' || ms.referencia ELSE '' END
              AS descripcion,
            ABS(ms.cantidad) AS monto,
            COALESCE(u.nombre, '') AS usuario,
            NULL          AS turno_id,
            ms.id         AS ref_id,
            'movimientos_stock' AS ref_tabla
        FROM movimientos_stock ms
        JOIN productos p ON p.id = ms.producto_id
        LEFT JOIN usuarios u ON u.id = ms.usuario_id
    """)

    # — Facturas —
    partes.append("""
        SELECT
            f.created_at  AS ts,
            f.fecha,
            'factura'     AS tipo,
            'Factura tipo ' || f.tipo ||
              ' N° ' || printf('%04d', f.punto_venta) ||
              '-' || printf('%08d', f.numero) ||
              CASE WHEN f.cliente_razon IS NOT NULL AND f.cliente_razon != ''
                   THEN ' — ' || f.cliente_razon ELSE '' END
              AS descripcion,
            f.total       AS monto,
            ''            AS usuario,
            NULL          AS turno_id,
            f.id          AS ref_id,
            'facturas'    AS ref_tabla
        FROM facturas f
    """)

    # — Turnos (apertura y cierre como eventos separados) —
    partes.append("""
        SELECT
            t.created_at  AS ts,
            DATE(t.apertura) AS fecha,
            'turno'       AS tipo,
            CASE t.estado
              WHEN 'abierto' THEN 'Turno #' || t.id || ' abierto — fondo $' || t.monto_inicial
              ELSE 'Turno #' || t.id || ' cerrado — declarado $' ||
                   COALESCE(CAST(t.monto_declarado_cierre AS TEXT), '0')
            END           AS descripcion,
            t.monto_inicial AS monto,
            COALESCE(u.nombre, '') AS usuario,
            t.id          AS turno_id,
            t.id          AS ref_id,
            'turnos_caja' AS ref_tabla
        FROM turnos_caja t
        JOIN usuarios u ON u.id = t.usuario_id
    """)

    # — Remitos —
    partes.append("""
        SELECT
            r.created_at  AS ts,
            r.date        AS fecha,
            'remito'      AS tipo,
            'Remito ' || r.number || ' — ' || r.client_name AS descripcion,
            r.total       AS monto,
            ''            AS usuario,
            NULL          AS turno_id,
            r.id          AS ref_id,
            'remitos'     AS ref_tabla
        FROM remitos r
    """)

    # — Presupuestos —
    partes.append("""
        SELECT
            p.created_at  AS ts,
            p.date        AS fecha,
            'presupuesto' AS tipo,
            'Presupuesto ' || p.number || ' — ' || p.client_name ||
              ' (' || p.status || ')' AS descripcion,
            p.total       AS monto,
            ''            AS usuario,
            NULL          AS turno_id,
            p.id          AS ref_id,
            'presupuestos' AS ref_tabla
        FROM presupuestos p
    """)

    # ── filtros post-UNION ──────────────────────────────────────────────────────
    where, params = [], []

    if tipos:
        marks = ",".join("?" * len(tipos))
        where.append(f"tipo IN ({marks})")
        params.extend(tipos)

    if usuario_id:
        # usuario solo está en ventas, stock, turnos; el resto da ''
        where.append("usuario_id_filter = ?")
        # se resuelve diferente — usamos subquery wrapper
    if desde:
        where.append("fecha >= ?"); params.append(desde)
    if hasta:
        where.append("fecha <= ?"); params.append(hasta)
    if turno_id:
        where.append("turno_id = ?"); params.append(turno_id)

    union_sql = "\nUNION ALL\n".join(partes)

    # Para filtrar por usuario necesitamos un wrapper con un JOIN auxiliar
    if usuario_id:
        # Re-construir solo las tablas que tienen usuario
        sql = f"""
            SELECT * FROM (
                {union_sql}
            ) sub
            WHERE usuario = (SELECT nombre FROM usuarios WHERE id=?)
        """
        params_final = [usuario_id] + params
        if where:
            sql += " AND " + " AND ".join(where)
    else:
        sql = f"""
            SELECT * FROM (
                {union_sql}
            ) sub
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        params_final = params

    sql += " ORDER BY ts DESC, ref_id DESC LIMIT ? OFFSET ?"
    params_final += [limit, offset]

    with get_connection() as conn:
        rows = conn.execute(sql, params_final).fetchall()
    return [dict(r) for r in rows]


def get_actividad_count(tipos=None, usuario_id=None, turno_id=None,
                        desde="", hasta="") -> int:
    """Cuenta total de filas para paginación."""
    rows = get_actividad_log(tipos=tipos, usuario_id=usuario_id, turno_id=turno_id,
                             desde=desde, hasta=hasta, limit=10000, offset=0)
    return len(rows)


# ── Módulos ────────────────────────────────────────────────────────────────────

def get_modulos() -> dict[str, bool]:
    """Devuelve {modulo: habilitado} para todos los módulos registrados."""
    with get_connection() as conn:
        rows = conn.execute("SELECT modulo, habilitado FROM modulos").fetchall()
    return {r["modulo"]: bool(r["habilitado"]) for r in rows}


def get_modulos_completo() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, modulo, habilitado, plan FROM modulos ORDER BY plan, modulo"
        ).fetchall()
    return [dict(r) for r in rows]


def set_modulo(modulo: str, habilitado: bool):
    with get_connection() as conn:
        conn.execute(
            "UPDATE modulos SET habilitado=? WHERE modulo=?",
            (1 if habilitado else 0, modulo),
        )


def apply_plan(plan: str):
    """Habilita/deshabilita módulos según el plan elegido."""
    _PLANES = {
        "basico":    {"clientes", "caja", "ventas"},
        "estandar":  {"clientes", "caja", "ventas", "facturacion", "remitos", "presupuestos", "productos"},
        "premium":   {"clientes", "caja", "ventas", "facturacion", "remitos", "presupuestos", "productos", "stock"},
    }
    activos = _PLANES.get(plan, set())
    with get_connection() as conn:
        rows = conn.execute("SELECT modulo FROM modulos").fetchall()
        for r in rows:
            conn.execute(
                "UPDATE modulos SET habilitado=?, plan=? WHERE modulo=?",
                (1 if r["modulo"] in activos else 0, plan, r["modulo"]),
            )


# ── Reportes ───────────────────────────────────────────────────────────────────

def get_reporte_ventas(desde: str = "", hasta: str = "", agrupacion: str = "dia") -> list[dict]:
    """Ventas agrupadas por día, semana o mes."""
    fmt = {"dia": "%Y-%m-%d", "semana": "%Y-W%W", "mes": "%Y-%m"}.get(agrupacion, "%Y-%m-%d")
    where, params = [], []
    if desde:
        where.append("fecha >= ?"); params.append(desde)
    if hasta:
        where.append("fecha <= ?"); params.append(hasta)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT strftime('{fmt}', fecha) AS periodo,
               COUNT(*) AS cantidad,
               ROUND(SUM(total), 2) AS total
        FROM ventas {w}
        GROUP BY periodo ORDER BY periodo
    """
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_reporte_medios_pago(desde: str = "", hasta: str = "") -> list[dict]:
    """Totales por medio de pago en el período."""
    where, params = [], []
    if desde:
        where.append("v.fecha >= ?"); params.append(desde)
    if hasta:
        where.append("v.fecha <= ?"); params.append(hasta)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT vp.medio, COUNT(DISTINCT vp.venta_id) AS operaciones,
               ROUND(SUM(vp.monto), 2) AS total
        FROM ventas_pagos vp
        JOIN ventas v ON v.id = vp.venta_id {w}
        GROUP BY vp.medio ORDER BY total DESC
    """
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_reporte_productos_top(desde: str = "", hasta: str = "", limit: int = 20) -> list[dict]:
    """Productos más vendidos (por cantidad y por monto) en el período."""
    where, params = [], []
    if desde:
        where.append("v.fecha >= ?"); params.append(desde)
    if hasta:
        where.append("v.fecha <= ?"); params.append(hasta)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT ji.value->>'$.nombre' AS nombre,
               ROUND(SUM(CAST(ji.value->>'$.qty' AS REAL)), 2) AS cantidad,
               ROUND(SUM(CAST(ji.value->>'$.qty' AS REAL) *
                         CAST(ji.value->>'$.precio' AS REAL)), 2) AS total
        FROM ventas v, json_each(v.items) ji {w}
        GROUP BY nombre ORDER BY cantidad DESC LIMIT ?
    """
    params.append(limit)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_reporte_caja(desde: str = "", hasta: str = "") -> list[dict]:
    """Movimientos de caja por tipo en el período."""
    where, params = [], []
    if desde:
        where.append("fecha >= ?"); params.append(desde)
    if hasta:
        where.append("fecha <= ?"); params.append(hasta)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT tipo, COUNT(*) AS cantidad, ROUND(SUM(monto), 2) AS total
        FROM caja_movimientos {w}
        GROUP BY tipo ORDER BY total DESC
    """
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_reporte_stock_bajo() -> list[dict]:
    """Productos con stock actual por debajo del mínimo."""
    sql = """
        SELECT p.id, p.nombre, p.codigo, p.stock_minimo,
               ROUND(COALESCE(SUM(ms.cantidad), 0), 3) AS stock_actual
        FROM productos p
        LEFT JOIN movimientos_stock ms ON ms.producto_id = p.id
        GROUP BY p.id
        HAVING stock_actual < p.stock_minimo
        ORDER BY (p.stock_minimo - stock_actual) DESC
    """
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql).fetchall()]


def get_reporte_resumen(desde: str = "", hasta: str = "") -> dict:
    """KPIs rápidos para el período."""
    where, params = [], []
    if desde:
        where.append("fecha >= ?"); params.append(desde)
    if hasta:
        where.append("fecha <= ?"); params.append(hasta)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    with get_connection() as conn:
        v = conn.execute(
            f"SELECT COUNT(*) cnt, ROUND(SUM(total),2) total FROM ventas {w}", params
        ).fetchone()
        f_row = conn.execute(
            f"SELECT COUNT(*) cnt FROM facturas {w}", params
        ).fetchone()
        caja = conn.execute(
            f"SELECT ROUND(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END),2) saldo FROM caja_movimientos {w}", params
        ).fetchone()
    return {
        "ventas_cantidad": v["cnt"] or 0,
        "ventas_total":    v["total"] or 0.0,
        "facturas_cantidad": f_row["cnt"] or 0,
        "caja_saldo":      caja["saldo"] or 0.0,
    }


def set_venta_mp_order(venta_id: int, mp_order_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE ventas SET mp_order_id=? WHERE id=?",
            (mp_order_id, venta_id),
        )
        conn.commit()


def set_venta_mp_payment(venta_id: int, mp_payment_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE ventas SET mp_payment_id=? WHERE id=?",
            (mp_payment_id, venta_id),
        )
        conn.commit()


def get_venta_by_mp_order(mp_order_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM ventas WHERE mp_order_id=?", (mp_order_id,)
        ).fetchone()
        return dict(row) if row else None


def add_venta_pago_referencia_mp(venta_id: int, payment_id: str) -> None:
    """Actualiza la referencia del pago MP/billetera de la venta con el payment_id."""
    with get_connection() as conn:
        # Actualizar referencia en el pago existente de medio mercadopago/billetera/cuenta_dni
        conn.execute(
            """UPDATE ventas_pagos SET referencia=?
               WHERE venta_id=? AND medio IN ('mercadopago','billetera','cuenta_dni','qr')
               AND (referencia IS NULL OR referencia='')""",
            (f"MP#{payment_id}", venta_id),
        )
        conn.commit()
