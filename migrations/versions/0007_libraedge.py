"""Las tablas del nodo offline (LibraEdge, E6 de la fase 1, 2026-10-19).

`node_identity`, `local_sequences`, `sync_outbox`, `sync_inbox` y `sync_changelog`. Llama a las funciones del paquete
en vez de re-expresar el DDL con `op.create_table(...)`, por el mismo motivo que la baseline: la fuente de verdad es el
DDL de LibraEdge, y re-escribirlo acá crearía **una segunda fuente que se desincroniza en el primer cambio** del motor.
Son las MISMAS funciones que llama `init_db()` (la instancia nueva y cada reinicio): las dos puntas convergen.

**Se crean en toda instancia, sea nodo o no** (como en RestoLibra, `0003_libraedge`). Un central que nunca corra
offline igual las necesita: `node_identity` para autenticar a los nodos que le pushean, `sync_inbox` para deduplicar
operaciones repetidas y `sync_changelog` para publicar la bajada. Crearlas sólo donde la instancia sea un nodo dejaría
el schema de unas instancias distinto del de otras **en silencio**. Por eso esta revisión **no consulta** la identidad
del nodo: corre igual en todas. En una instancia sin nodos (Compulibra) son tablas vacías que nadie escribe.

Idempotente (`CREATE TABLE IF NOT EXISTS`): corre igual sobre una instancia viva que sobre una base vacía. Aditiva: no
toca ninguna tabla existente.

> El trigger del changelog **no** se instala acá. Publicar una tabla al changelog es una decisión de aprovisionamiento
> del central —qué se espeja hacia qué nodo— (`libraedge-central nodo publicar`), no parte del schema del producto.
"""
from alembic import op
from libracore.db.migraciones import conexion_libracore
from libraedge.db.changelog import init_changelog_schema
from libraedge.db.schema import init_schema as init_edge_schema

revision = "0007_libraedge"
down_revision = "0006_sucursal_unica"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `conexion_libracore` envuelve el bind de Alembic en la conexión que espera el DDL de la familia: traduce los `?`,
    # el `INTEGER PRIMARY KEY AUTOINCREMENT` y saltea el `PRAGMA foreign_keys = ON` con el que arranca `init_schema()`
    # de LibraEdge, que contra PostgreSQL reventaría.
    conn = conexion_libracore(op.get_bind())
    init_edge_schema(conn)
    init_changelog_schema(conn)


def downgrade() -> None:
    # Bajar esta revisión es tirar el outbox: las operaciones que un nodo generó durante un corte y todavía no confirmó
    # no están en ningún otro lado. En una instancia sin nodos están vacías, pero la revisión no lo distingue.
    raise NotImplementedError(
        "No se baja: el outbox puede tener operaciones sin sincronizar, que no existen en ninguna otra parte. Para "
        "volver atrás, restaurar el backup."
    )
