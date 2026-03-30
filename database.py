import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "remitos.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                address     TEXT,
                cuit_dni    TEXT,
                email       TEXT,
                phone       TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
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
        """)


# ── Clients ────────────────────────────────────────────────────────────────────

def create_client(name, address="", cuit_dni="", email="", phone=""):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO clients (name, address, cuit_dni, email, phone) VALUES (?,?,?,?,?)",
            (name, address, cuit_dni, email, phone),
        )
        return cur.lastrowid


def get_all_clients():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM clients ORDER BY name")]


def get_client(client_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        return dict(row) if row else None


def update_client(client_id, name=None, address=None, cuit_dni=None, email=None, phone=None):
    client = get_client(client_id)
    if not client:
        return
    with get_connection() as conn:
        conn.execute(
            """UPDATE clients SET name=?, address=?, cuit_dni=?, email=?, phone=?
               WHERE id=?""",
            (
                name    if name    is not None else client["name"],
                address if address is not None else client["address"],
                cuit_dni if cuit_dni is not None else client["cuit_dni"],
                email   if email   is not None else client["email"],
                phone   if phone   is not None else client["phone"],
                client_id,
            ),
        )


def delete_client(client_id):
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM remitos WHERE client_id=?", (client_id,)
        ).fetchone()[0]
        if count > 0:
            raise ValueError(f"El cliente tiene {count} remito(s) asociado(s) y no puede eliminarse.")
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
