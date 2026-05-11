import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "contalibra.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
