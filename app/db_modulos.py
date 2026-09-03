"""Shim: la lógica de módulos ahora vive en libracore.db.modulos."""
from libracore.db.core import get_connection
from libracore.db.modulos import apply_plan, get_modulos  # noqa: F401


def set_addon(nombre: str, habilitado: bool) -> None:
    """Habilita o deshabilita un add-on (módulo suelto) en ESTA instancia.

    Un add-on (`plans.ADDONS`, ej. `mayorista`) no pertenece a ningún plan, así
    que `apply_plan`/`set_plan` no lo tocan; se prende/apaga por instancia con
    esta función. Idempotente: crea la fila si falta (con `plan="addon"`, igual
    que el seed) y setea `habilitado`.

    NO valida que `nombre` sea un add-on real — eso lo hace la CLI
    (`panel_admin.py addon`) contra `plans.ADDONS`, que es quien decide qué es
    un add-on. Corre dentro del contenedor del cliente (vía `docker exec`), donde
    `libracore.db.core` ya apunta al PostgreSQL de la instancia.
    """
    on = 1 if habilitado else 0
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO modulos (modulo, habilitado, plan) VALUES (?,?,?)",
            (nombre, on, "addon"),
        )
        conn.execute("UPDATE modulos SET habilitado=? WHERE modulo=?", (on, nombre))
