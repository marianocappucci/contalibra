"""
Movimientos de stock (entradas, salidas, ajustes, descuento por venta) y
consulta de stock actual. Extraído de database.py como parte del split en
módulos lógicos (Fase 3 de LibraCore, sub-paso previo dentro de cada
producto, sin cambiar comportamiento — ver wiki/entities/libracore.md).
"""
import sqlite3
import contextlib

from db_core import get_connection
from db_productos import get_default_deposito_id


def add_movimiento_stock(producto_id: int, tipo: str, cantidad: float,
                         referencia: str = "", fecha: str = "",
                         venta_id: int | None = None,
                         usuario_id: int | None = None,
                         deposito_id: int | None = None,
                         conn: sqlite3.Connection | None = None):
    """Agrega un movimiento de stock. cantidad positiva=entrada, negativa=salida."""
    from datetime import date as _date
    _fecha = fecha or _date.today().isoformat()
    _deposito = deposito_id or get_default_deposito_id()
    cm = contextlib.nullcontext(conn) if conn is not None else get_connection()
    with cm as c:
        c.execute(
            """INSERT INTO movimientos_stock
               (producto_id, tipo, cantidad, referencia, venta_id, usuario_id, fecha, deposito_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (producto_id, tipo, cantidad, referencia, venta_id, usuario_id, _fecha, _deposito),
        )


def get_stock_actual(producto_id: int) -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(cantidad),0) FROM movimientos_stock WHERE producto_id=?",
            (producto_id,),
        ).fetchone()
    return float(row[0])


def get_stock_todos() -> list[dict]:
    """Devuelve todos los productos con su stock actual."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT p.id, p.codigo, p.nombre, p.unidad, p.categoria,
                   p.stock_minimo, p.activo,
                   COALESCE(SUM(m.cantidad), 0) AS stock_actual
            FROM productos p
            LEFT JOIN movimientos_stock m ON m.producto_id = p.id
            WHERE p.activo = 1
            GROUP BY p.id
            ORDER BY p.nombre
        """).fetchall()
    return [dict(r) for r in rows]


def get_movimientos_stock(producto_id: int | None = None,
                          desde: str = "", hasta: str = "",
                          limit: int = 200) -> list[dict]:
    with get_connection() as conn:
        where, params = [], []
        if producto_id:
            where.append("m.producto_id = ?"); params.append(producto_id)
        if desde:
            where.append("m.fecha >= ?"); params.append(desde)
        if hasta:
            where.append("m.fecha <= ?"); params.append(hasta)
        sql = """SELECT m.*, p.nombre AS producto_nombre, p.unidad
                 FROM movimientos_stock m
                 JOIN productos p ON p.id = m.producto_id"""
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY m.fecha DESC, m.id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def ajustar_stock(producto_id: int, stock_nuevo: float, referencia: str,
                  usuario_id: int | None = None, fecha: str = ""):
    """Crea un movimiento de ajuste para llevar el stock al valor indicado."""
    actual = get_stock_actual(producto_id)
    delta  = round(stock_nuevo - actual, 4)
    if delta == 0:
        return
    add_movimiento_stock(
        producto_id=producto_id, tipo="ajuste",
        cantidad=delta, referencia=referencia,
        usuario_id=usuario_id, fecha=fecha,
    )


def descontar_stock_venta(venta_id: int, items: list, fecha: str = "",
                           usuario_id: int | None = None,
                           conn: sqlite3.Connection | None = None):
    """Descuenta stock por cada ítem de la venta que tenga producto_id."""
    for item in items:
        pid = item.get("producto_id")
        if not pid:
            continue
        add_movimiento_stock(
            producto_id=pid, tipo="venta",
            cantidad=-abs(float(item.get("qty", 0))),
            referencia=f"Venta ID {venta_id}",
            venta_id=venta_id, usuario_id=usuario_id, fecha=fecha,
            conn=conn,
        )
