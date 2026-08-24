"""Ventas que entran desde otro producto de la familia.

El caso que la estrena es [[medlibra]]: el consultorio completa un turno y lo
manda a facturar acá, que es donde vive la contabilidad. Pero nada de esto es
específico de salud — es "una venta que no la cargó una persona en el
mostrador".

## 🔴 Por qué hace falta un usuario, y no alcanza el token de servicio

El token de servicio de libraauth **no es un usuario**: su `SERVICE_USER["id"]`
es `None`. Y en Contalibra el `usuario_id` de una venta no es una etiqueta de
auditoría — es lo que la engancha al **turno de caja abierto**:

```python
if usuario_id:
    turno = get_turno_activo(usuario_id, conn=conn)
    if turno:
        vincular_venta_turno(venta_id, turno["id"], conn=conn)
```

(`db_ventas.crear_venta_directa`). Una venta creada con el token y sin usuario
entra a la base, suma su movimiento de caja y queda **fuera de todo turno**: el
cierre de caja no la ve, y la diferencia aparece como un descuadre que nadie
sabe de dónde sale.

Por eso la instancia configura **una vez** qué usuario representa a las
integraciones, y las ventas externas se atribuyen a él. Quién es lo decide
Contalibra, no el producto que manda: si viniera en el pedido, cualquiera que
tenga el token podría atribuirle ventas a cualquier usuario.

## La idempotencia va por referencia externa

El producto que manda puede reintentar —un timeout, un deploy en el medio— y un
reintento no puede facturar dos veces la misma consulta. Cada venta externa
queda atada a `(sistema, referencia)`, único; si llega repetida se devuelve la
venta que ya existe en vez de crear otra.

Va en tabla aparte y no en una columna de `sales` por lo mismo que `venta_links`
—que es el precedente de esta casa—: `sales` es de LibraCommerce y no tiene por
qué saber de qué producto de la suite vino una venta.
"""
# Desde `app.db_core` y no desde `libracore.db.core`: importarlo es lo que
# garantiza que `configure()` ya corrió con el destino de ESTA instancia. Es la
# convención del resto de los `db_*.py` de acá.
from app.db_core import _ar_now, get_connection

#: Clave de `integraciones_config` con el **username** del usuario al que se
#: atribuyen las ventas externas.
USUARIO_INTEGRACIONES = "usuario_integraciones"


def crear_tablas(conn) -> None:
    """Las dos tablas de este módulo. Idempotente, la llama `init_db()`."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS integraciones_config (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)
    # `UNIQUE (sistema, referencia)` es la idempotencia. Sin eso, un reintento
    # del producto emisor crea una segunda venta con su segunda factura, y la
    # única forma de darse cuenta es que a fin de mes no cierre.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ventas_origen_externo (
            venta_id   INTEGER PRIMARY KEY REFERENCES sales(id) ON DELETE CASCADE,
            sistema    TEXT NOT NULL,
            referencia TEXT NOT NULL,
            creado_en  TEXT NOT NULL,
            UNIQUE (sistema, referencia)
        )
    """)


# ── El usuario de integraciones ────────────────────────────────────────────

def get_usuario_integraciones() -> str:
    """El username configurado, o `""` si la instancia no lo configuró."""
    with get_connection() as conn:
        fila = conn.execute(
            "SELECT valor FROM integraciones_config WHERE clave = ?",
            (USUARIO_INTEGRACIONES,),
        ).fetchone()
    return fila["valor"] if fila else ""


def set_usuario_integraciones(username: str) -> None:
    """Fija el username. `""` lo desconfigura, que **apaga** la integración:
    sin usuario, el endpoint rechaza en vez de crear ventas sin dueño."""
    with get_connection() as conn:
        if not username:
            conn.execute(
                "DELETE FROM integraciones_config WHERE clave = ?",
                (USUARIO_INTEGRACIONES,),
            )
        else:
            # 🔴 `ON CONFLICT ... DO UPDATE` y **no `INSERT OR REPLACE`**: el
            # adaptador de PostgreSQL de LibraCore traduce `INSERT OR IGNORE`
            # pero no `OR REPLACE`, así que ese verbo llega crudo y revienta con
            # un error de sintaxis. Esta forma la entienden los dos motores —es
            # la que ya usa `libracore/db/listas_precio.py`— y lo encontró
            # correr la suite contra `postgres:16`, no leer el código.
            conn.execute(
                "INSERT INTO integraciones_config (clave, valor) VALUES (?,?)"
                " ON CONFLICT (clave) DO UPDATE SET valor = excluded.valor",
                (USUARIO_INTEGRACIONES, username),
            )
        conn.commit()


# ── El origen externo de una venta ─────────────────────────────────────────

def get_venta_por_referencia(sistema: str, referencia: str) -> int | None:
    with get_connection() as conn:
        fila = conn.execute(
            "SELECT venta_id FROM ventas_origen_externo"
            " WHERE sistema = ? AND referencia = ?",
            (sistema, referencia),
        ).fetchone()
    return fila["venta_id"] if fila else None


def registrar_origen(venta_id: int, sistema: str, referencia: str, conn=None) -> None:
    """Ata la venta a su referencia externa.

    Acepta `conn` para poder ir **en la misma transacción** que la venta: si se
    hiciera después y en su propia conexión, un corte entre las dos dejaría una
    venta sin referencia — y el reintento siguiente la volvería a crear, que es
    exactamente lo que esta tabla existe para impedir.
    """
    sql = ("INSERT INTO ventas_origen_externo (venta_id, sistema, referencia, creado_en)"
           " VALUES (?,?,?,?)")
    # `_ar_now()` de esta casa devuelve un **string** `YYYY-MM-DD HH:MM:SS`, no
    # un datetime: es el mismo formato que guardan las demás tablas de acá.
    valores = (venta_id, sistema, referencia, _ar_now())
    if conn is not None:
        conn.execute(sql, valores)
        return
    with get_connection() as propia:
        propia.execute(sql, valores)
        propia.commit()


def get_origen_de_venta(venta_id: int) -> dict | None:
    with get_connection() as conn:
        fila = conn.execute(
            "SELECT sistema, referencia, creado_en FROM ventas_origen_externo"
            " WHERE venta_id = ?",
            (venta_id,),
        ).fetchone()
    return dict(fila) if fila else None
