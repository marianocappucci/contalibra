"""cliente_lista_precio: la asociación cliente → lista de precios (add-on mayorista).

Pegamento entre `clients` de LibraCore y `price_lists` de LibraCommerce,
agregada DESPUÉS de que `app/schema_propio.py` quedó congelado en la `0001`.
El DDL vivía en `db_mayorista.crear_tabla_cliente_lista_precio`; desde el
2026-09-28 (ADR-010 de libracommerce) es del motor
(`erp.schema.crear_cliente_lista_precio`, mismo criterio que `venta_links`) —
`app/db_mayorista.py` se retiró. La revisión sigue creando **la misma tabla**
(idéntico DDL, `CREATE TABLE IF NOT EXISTS`): una instancia ya migrada no
cambia nada al correrla de nuevo. Llamada por esta revisión y por `init_db()`
— la MISMA función en las dos puntas, como la `0001` con `init_schema_propio`,
para que una instancia nueva (nace de la cadena) y una vieja (nació del
arranque) no diverjan. Lo sostiene `tests/test_schema_propio_congelado.py`.

🔴 Corre DESPUÉS de `0001` (que llama a `init_commerce_schema`, creando
`price_lists`) y después de la cadena de LibraCore (que crea `clients`): las dos
FK necesitan sus tablas destino. En un alta, `libracore-migrar` va primero en la
declaración de `migraciones`, así que ambas existen cuando corre esta revisión.
"""
from alembic import op
from libracommerce.erp.schema import crear_cliente_lista_precio
from libracore.db.migraciones import conexion_libracore

revision = "0002_cliente_lista_precio"
down_revision = "0001_baseline_contalibra"
branch_labels = None
depends_on = None


def upgrade():
    # `conexion_libracore` envuelve el bind de Alembic en la conexión de la
    # familia (traduce PRAGMA y excepciones), igual que en la `0001`.
    conn = conexion_libracore(op.get_bind())
    crear_cliente_lista_precio(conn)


def downgrade():
    op.drop_table("cliente_lista_precio")
