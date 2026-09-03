"""Add-on mayorista: la asociación cliente → lista de precios.

El paquete mayorista (add-on gateado `mayorista`, ver `plans.py::ADDONS` y
wiki/analyses/distribuidora-mayorista-producto-candidato) le asigna a cada
cliente una lista de precios por defecto. La asociación vive en una tabla
**propia de Contalibra**, no en el motor: es pegamento entre `clients`
(LibraCore) y `price_lists` (LibraCommerce), mismo criterio que `venta_links`.
NO es una columna en `clients` —tabla del motor, transversal a los ocho
productos— sino una tabla aparte.

🔴 La tabla se crea desde `crear_tabla_cliente_lista_precio`, llamada por
`init_db()` (cada arranque, y el harness de tests) Y por la revisión de Alembic
`0002_cliente_lista_precio` (el deploy). Es el mismo patrón que las 3 tablas de
`app/schema_propio.py`, que NO se toca: quedó congelada en la revisión `0001`.
Poner esta tabla adentro de esa función la descongelaría; ponerla sólo en la
revisión la dejaría afuera del arranque —y del harness, que no corre Alembic—.
"""
from libracore.db.core import get_connection


def crear_tabla_cliente_lista_precio(conn) -> None:
    """La tabla propia `cliente_lista_precio`. Idempotente (`IF NOT EXISTS`).

    Una fila por cliente (PK sobre `cliente_id`): un cliente tiene a lo sumo una
    lista asignada. Ambas FK con `ON DELETE CASCADE` — si se borra el cliente o
    la lista, la asociación se va sola en vez de quedar colgada.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cliente_lista_precio (
            cliente_id INTEGER PRIMARY KEY REFERENCES clients(id) ON DELETE CASCADE,
            lista_id   INTEGER NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE
        )
    """)


def get_lista_de_cliente(cliente_id: int) -> int | None:
    """El `lista_id` asignado al cliente, o `None` si no tiene ninguno."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT lista_id FROM cliente_lista_precio WHERE cliente_id=?",
            (cliente_id,),
        ).fetchone()
    return row["lista_id"] if row else None


def set_lista_de_cliente(cliente_id: int, lista_id: int) -> None:
    """Asigna (o reasigna) la lista del cliente.

    Upsert por `DELETE` + `INSERT` en una sola transacción, para no depender de
    la sintaxis de `ON CONFLICT` (que difiere entre SQLite y PostgreSQL).
    """
    with get_connection() as conn:
        conn.execute("DELETE FROM cliente_lista_precio WHERE cliente_id=?", (cliente_id,))
        conn.execute(
            "INSERT INTO cliente_lista_precio (cliente_id, lista_id) VALUES (?,?)",
            (cliente_id, lista_id),
        )


def quitar_lista_de_cliente(cliente_id: int) -> None:
    """Saca la asignación del cliente (vuelve a cotizar con el precio base)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM cliente_lista_precio WHERE cliente_id=?", (cliente_id,))
