"""El schema **propio** de Contalibra: lo que no es de ningún motor.

De las 61 tablas de una instancia, **3 son de este producto**. Las otras 58 las
declaran los motores, y cada uno las mantiene por su cuenta:

| Quién | Tablas | Cómo evoluciona su schema |
|---|---|---|
| `libracore` | 33 | cadena de Alembic (`alembic_version`), vía `libracore-migrar` |
| `libracommerce` | 19 + `schema_migrations` | runner numerado propio, dentro de `init_schema()` |
| `libraauth` | 5 (`usuarios`, `auth_log`, `demo_codigos`, `password_reset_tokens`, `smtp_settings`, `aceptaciones_terminos`) | `Base.metadata.create_all()` al arrancar |
| **Contalibra** | **`venta_links`, `integraciones_config`, `ventas_origen_externo`** | **esta función + `alembic/versions/`** |

Este módulo existe para que esas tres tengan **una sola fuente de verdad**. Antes
el DDL de `venta_links` vivía suelto adentro de `init_db()`, mezclado con seeds y
con las llamadas a los motores: la baseline de Alembic habría tenido que
re-expresarlo y desde el primer cambio habrían sido dos fuentes que se
desincronizan. Acá la baseline **llama a esta función**, igual que la `0001` de
LibraCore llama a `init_core_schema()`.

🔴 **Desde la revisión `0001`, esta función es de sólo lectura.** Todo cambio de
schema de las tablas de arriba va como revisión nueva en `alembic/versions/`, no
como línea agregada acá. El motivo es el de siempre: `CREATE TABLE IF NOT EXISTS`
crea lo que no está y **no altera lo que sí**, así que una columna agregada acá
llega a las instancias nuevas y deja las viejas atrás, en silencio. Lo sostiene
`tests/test_schema_propio_congelado.py`, que compara el resultado contra una
fixture.

Es idempotente a propósito —`CREATE TABLE IF NOT EXISTS` y `ALTER` guardados por
introspección—, que es lo que permite correr la baseline sobre una instancia
viva: hace lo mismo que ya hace cada arranque, más registrar la versión.
"""
from app.db_integraciones import crear_tablas as _crear_tablas_integraciones


def init_schema_propio(conn) -> None:
    """Las 3 tablas propias de Contalibra. Idempotente.

    La llaman `init_db()` (en cada arranque) y la baseline `0001` (en el
    deploy). Las dos con una conexión de `libracore.db.core`, que es la que
    traduce los `PRAGMA` y las excepciones entre SQLite y PostgreSQL.
    """
    # Referencias cruzadas entre la venta (LibraCommerce) y contextos que no son
    # suyos: facturación/remitos y turno de caja (LibraCore) y MercadoPago. No
    # van dentro de `sales` para no meter dominio ajeno en el motor genérico —
    # ver db_ventas.py.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS venta_links (
            venta_id      INTEGER PRIMARY KEY REFERENCES sales(id) ON DELETE CASCADE,
            factura_id    INTEGER REFERENCES facturas(id) ON DELETE SET NULL,
            remito_id     INTEGER REFERENCES remitos(id) ON DELETE SET NULL,
            turno_id      INTEGER REFERENCES turnos_caja(id) ON DELETE SET NULL,
            mp_order_id   TEXT DEFAULT '',
            mp_payment_id TEXT DEFAULT ''
        )
    """)

    # Ventas que entran desde otro producto de la familia, y el usuario al que se
    # atribuyen. Mismo criterio que `venta_links`: de qué producto de la suite
    # vino una venta no es dominio de LibraCommerce. Ver `db_integraciones.py`.
    _crear_tablas_integraciones(conn)
