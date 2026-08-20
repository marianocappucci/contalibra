"""Los números de esta instancia, agregados, para el panel del dueño.

Existe porque el panel consolida **cinco sucursales** y para eso necesita
totales, no listados. La diferencia no es cosmética:

🔴 `libracore.db.dashboard.get_dashboard_data` devuelve `facturas_sin_cobrar`
con **`LIMIT 8`**. Es una muestra para pintar una tarjeta, y alcanza para una
pantalla. Consolidando cinco instancias, sumar esas muestras daría "40 sin
cobrar" cuando el número real puede ser cualquiera: sería el tope, no el dato.
Acá se cuenta.

Vive en el producto y no en [[libracore]] porque hoy el único consumidor es
Contalibra. Cuando un segundo producto necesite el panel, se muda al motor —
que es donde ya viven las consultas de facturas y caja.
"""
from libracore.db.caja import sql_no_es_cuenta_corriente

from app.db_core import get_connection

#: Los tipos que son factura. Las notas de crédito y débito quedan afuera de
#  "facturado": restan o suman por otro lado y mezclarlas infla el número.
_TIPOS_FACTURA = (1, 6, 11)


def get_resumen(desde: str, hasta: str) -> dict:
    """Totales del período. Todo en una conexión, todo con COUNT/SUM."""
    ph = ",".join("?" * len(_TIPOS_FACTURA))
    tipos = list(_TIPOS_FACTURA)

    with get_connection() as conn:
        facturado, comprobantes = conn.execute(
            f"SELECT COALESCE(SUM(total), 0), COUNT(*) FROM facturas "
            f"WHERE tipo IN ({ph}) AND fecha BETWEEN ? AND ?",
            tipos + [desde, hasta],
        ).fetchone()

        cobrado, egresos = conn.execute(
            """SELECT
                 COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE 0 END), 0),
                 COALESCE(SUM(CASE WHEN tipo='egreso'  THEN monto ELSE 0 END), 0)
               FROM caja_movimientos WHERE fecha BETWEEN ? AND ?""",
            (desde, hasta),
        ).fetchone()

        # El saldo es histórico a propósito: es cuánta plata hay, no cuánta
        # entró en el período.
        saldo_caja = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END), 0) "
            "FROM caja_movimientos"
        ).fetchone()[0]

        # Sin cobrar: TODAS las que quedan impagas, no las del período. Una
        # factura de marzo sin cobrar sigue siendo plata que falta en agosto.
        #
        # 🔴 La condición de "cobrada" sale de `sql_no_es_cuenta_corriente()`, de
        # libracore, y no se reescribe acá. La primera versión de esta consulta
        # miraba sólo `factura_id IS NULL` y contaba como cobrada una factura
        # pagada a cuenta corriente — que es plata que **no entró**, y que la
        # pantalla del producto muestra como pendiente. Dos definiciones de
        # "cobrada" en el mismo sistema es exactamente lo que hay que evitar; lo
        # encontró un test con nueve facturas a cuenta corriente, que daba 0.
        sin_cobrar_cant, sin_cobrar_monto = conn.execute(
            f"""SELECT COUNT(*), COALESCE(SUM(f.total), 0)
                FROM facturas f
                LEFT JOIN caja_movimientos c
                       ON c.factura_id = f.id
                      AND c.tipo = 'ingreso'
                      AND {sql_no_es_cuenta_corriente('c.medio_pago')}
                WHERE f.tipo IN ({ph}) AND c.id IS NULL""",
            tipos,
        ).fetchone()

        ventas_cant, ventas_monto = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM sales "
            "WHERE status != 'cancelled' AND occurred_on BETWEEN ? AND ?",
            (desde, hasta),
        ).fetchone()

        # Bajo mínimo, no sin stock: el mínimo es el que el negocio configuró, y
        # `min_stock = 0` significa "no me avises", no "avisame siempre".
        bajo_minimo = conn.execute(
            """SELECT COUNT(*) FROM (
                 SELECT i.id
                 FROM catalog_items i
                 LEFT JOIN stock_movements m ON m.item_id = i.id
                 WHERE i.active = 1 AND i.min_stock > 0
                 GROUP BY i.id, i.min_stock
                 HAVING COALESCE(SUM(m.quantity_delta), 0) <= i.min_stock
               ) AS bajos"""
        ).fetchone()[0]

    return {
        "periodo": {"desde": desde, "hasta": hasta},
        "facturado": float(facturado),
        "cobrado": float(cobrado),
        "egresos": float(egresos),
        "saldo_caja": float(saldo_caja),
        "comprobantes": int(comprobantes),
        "sin_cobrar": {
            "cantidad": int(sin_cobrar_cant),
            "monto": float(sin_cobrar_monto),
        },
        "ventas": {
            "cantidad": int(ventas_cant),
            "monto": float(ventas_monto),
        },
        "stock_bajo_minimo": int(bajo_minimo),
    }
