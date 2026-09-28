"""reenvio_correo: destino externo al que se reenvía la casilla de la instancia.

Tabla propia de Contalibra, agregada DESPUÉS de que `app/schema_propio.py`
quedó congelado en la `0001`, mismo patrón que `0002_cliente_lista_precio`:
el DDL vive en `db_reenvio_correo.crear_tabla_reenvio_correo`, llamada por
esta revisión y por `init_db()` — la MISMA función en las dos puntas, para
que una instancia nueva (nace de la cadena) y una vieja (nació del arranque)
no diverjan. Lo sostiene `tests/test_schema_propio_congelado.py`.

Numerada `0004` y no `0003`: mientras esto se desarrollaba, `develop` sumó
`0003_cierres_diarios_hora_ar` (también hija de `0002`) — dos revisiones
`0003` con el mismo padre habrían dejado la cadena con dos heads. Encadenada
después de esa, no de `0002` directo.

Sin FK propia: no depende de una tabla que otra revisión cree, más allá de
la que ya exige su lugar en la cadena.
"""
from alembic import op
from libracore.db.migraciones import conexion_libracore

from app.db_reenvio_correo import crear_tabla_reenvio_correo

revision = "0004_reenvio_correo"
down_revision = "0003_cierres_diarios_hora_ar"
branch_labels = None
depends_on = None


def upgrade():
    conn = conexion_libracore(op.get_bind())
    crear_tabla_reenvio_correo(conn)


def downgrade():
    op.drop_table("reenvio_correo")
