"""Correo de reenvío: a qué dirección externa se reenvía lo que llega a la
casilla de la instancia (`<slug>@contalibra.com.ar`).

El cliente lo carga desde SU propio panel (sesión de admin normal, no
superadmin). Un proceso central, fuera de este repo, lee este valor por API y
reenvía ahí lo que le llega a la casilla de correo del servidor aparte. Acá
sólo se guarda el destino y se expone para que ese proceso lo lea — no hay
ningún reenvío real de este lado.

🔴 La tabla se crea desde `crear_tabla_reenvio_correo`, llamada por `init_db()`
(cada arranque, y el harness de tests) Y por la revisión de Alembic
`0004_reenvio_correo` (el deploy). Mismo patrón que `db_mayorista.py` —tabla
propia de Contalibra agregada DESPUÉS de que `app/schema_propio.py` quedó
congelado en la `0001`—.
"""
from app.db_core import _ar_now, get_connection

# La tabla tiene una sola fila y su id es fijo, mismo criterio que
# `smtp_settings` (libraauth, ver `FILA_UNICA` en `libraauth/smtp_settings.py`):
# un id autoincremental permitiría que un bug dejara dos filas y que la app
# usara cualquiera de las dos según el orden de lectura.
FILA_UNICA = 1


def crear_tabla_reenvio_correo(conn) -> None:
    """La tabla propia `reenvio_correo`. Idempotente (`IF NOT EXISTS`)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reenvio_correo (
            id            INTEGER PRIMARY KEY,
            destino       TEXT,
            actualizado_en TEXT NOT NULL
        )
    """)


def get_destino_reenvio() -> str | None:
    """El destino configurado, o `None` si la instancia no cargó ninguno."""
    with get_connection() as conn:
        fila = conn.execute(
            "SELECT destino FROM reenvio_correo WHERE id = ?", (FILA_UNICA,)
        ).fetchone()
    return fila["destino"] if fila else None


def set_destino_reenvio(destino: str | None) -> None:
    """Crea o actualiza la fila única. `destino=None` borra el reenvío —vuelve
    a leerse `None` hasta que se cargue otro—."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO reenvio_correo (id, destino, actualizado_en)"
            " VALUES (?,?,?)"
            " ON CONFLICT (id) DO UPDATE SET destino = excluded.destino,"
            " actualizado_en = excluded.actualizado_en",
            (FILA_UNICA, destino, _ar_now()),
        )
        conn.commit()
