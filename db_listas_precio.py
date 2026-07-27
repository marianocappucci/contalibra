"""Listas de precio de Contalibra.

Las tablas `listas_precio`/`lista_precio_items` **siguen siendo de
LibraCore** — no se migran a `price_lists`/`item_prices` de LibraCommerce:
ese es otro modelo (vigencias, quiebres de cantidad, precio por sucursal) y
mapear el modelo simple de Contalibra ahí es un proyecto propio, no parte de
P7.

Lo único que cambia es de dónde salen los productos: **tres de sus funciones
hacen `JOIN productos`**, y en Contalibra el catálogo vive en `catalog_items`
desde P7 (ver `db_productos.py`). El resto del módulo se re-exporta tal cual
de LibraCore, que **no se toca** — Restolibra sigue funcionando igual.

La FK de `lista_precio_items.producto_id` se reapunta a `catalog_items(id)`
en la migración de datos; como los IDs se preservaron, las filas existentes
siguen siendo válidas sin tocarlas.
"""
from libracore.db.core import get_connection
from libracore.db.listas_precio import (  # noqa: F401
    get_all_listas_precio,
    get_lista_precio,
    create_lista_precio,
    update_lista_precio,
    delete_lista_precio,
    get_precio_en_lista,
    get_precios_lista_dict,
    save_lista_precio_items,
)


def get_lista_precio_items(lista_id: int, categoria: str = "") -> list[dict]:
    with get_connection() as conn:
        where = "AND cat.name=?" if categoria else ""
        params = [lista_id]
        if categoria:
            params.append(categoria)
        rows = conn.execute(f"""
            SELECT ci.id, ic.code AS codigo, ci.name AS nombre, ci.unit_code AS unidad,
                   COALESCE(cat.name, '') AS categoria,
                   ci.default_sale_price AS precio_venta, ci.default_cost AS precio_costo,
                   COALESCE(lpi.precio, 0) AS precio_lista,
                   CASE WHEN lpi.producto_id IS NOT NULL THEN 1 ELSE 0 END AS en_lista
            FROM catalog_items ci
            LEFT JOIN categories cat ON cat.id = ci.category_id
            LEFT JOIN item_codes ic ON ic.item_id = ci.id AND ic.is_primary = 1
            LEFT JOIN lista_precio_items lpi
                   ON lpi.lista_id=? AND lpi.producto_id=ci.id
            WHERE ci.active=1 {where}
            ORDER BY categoria, ci.name
        """, params).fetchall()
    return [dict(r) for r in rows]


def apply_porcentaje_lista(lista_id: int, porcentaje: float,
                           base: str = "lista", categoria: str = "") -> int:
    """Aplica un ajuste porcentual a los precios de la lista.

    base: 'lista' (sobre precio actual), 'venta' (sobre precio_venta), 'costo' (sobre precio_costo).
    Devuelve la cantidad de productos actualizados.
    """
    factor = 1 + porcentaje / 100
    with get_connection() as conn:
        cat_where = "AND cat.name=?" if categoria else ""
        cat_param = [categoria] if categoria else []

        if base == "lista":
            # Actualiza solo los que ya tienen precio en la lista
            rows = conn.execute(f"""
                SELECT lpi.producto_id, lpi.precio
                FROM lista_precio_items lpi
                JOIN catalog_items ci ON ci.id = lpi.producto_id
                LEFT JOIN categories cat ON cat.id = ci.category_id
                WHERE lpi.lista_id=? AND ci.active=1 {cat_where}
            """, [lista_id] + cat_param).fetchall()
            for r in rows:
                nuevo = round(r["precio"] * factor, 2)
                conn.execute(
                    "UPDATE lista_precio_items SET precio=? WHERE lista_id=? AND producto_id=?",
                    (nuevo, lista_id, r["producto_id"]),
                )
            return len(rows)
        else:
            col = "default_sale_price" if base == "venta" else "default_cost"
            rows = conn.execute(f"""
                SELECT ci.id, ci.{col} AS base_precio
                FROM catalog_items ci
                LEFT JOIN categories cat ON cat.id = ci.category_id
                WHERE ci.active=1 {cat_where}
            """, cat_param).fetchall()
            for r in rows:
                nuevo = round(r["base_precio"] * factor, 2)
                conn.execute(
                    """INSERT INTO lista_precio_items (lista_id, producto_id, precio)
                       VALUES (?,?,?)
                       ON CONFLICT(lista_id, producto_id) DO UPDATE SET precio=excluded.precio""",
                    (lista_id, r["id"], nuevo),
                )
            return len(rows)


def importar_precios_lista(lista_id: int, fuente: str, fuente_lista_id: int | None = None):
    """Importa precios a la lista desde otra fuente.

    fuente: 'venta', 'costo', 'lista' (requiere fuente_lista_id).
    """
    with get_connection() as conn:
        if fuente == "lista" and fuente_lista_id:
            rows = conn.execute(
                "SELECT producto_id, precio FROM lista_precio_items WHERE lista_id=?",
                (fuente_lista_id,),
            ).fetchall()
            for r in rows:
                conn.execute(
                    """INSERT INTO lista_precio_items (lista_id, producto_id, precio)
                       VALUES (?,?,?)
                       ON CONFLICT(lista_id, producto_id) DO UPDATE SET precio=excluded.precio""",
                    (lista_id, r["producto_id"], r["precio"]),
                )
        else:
            col = "default_sale_price" if fuente == "venta" else "default_cost"
            rows = conn.execute(
                f"SELECT id, {col} AS precio FROM catalog_items WHERE active=1"
            ).fetchall()
            for r in rows:
                conn.execute(
                    """INSERT INTO lista_precio_items (lista_id, producto_id, precio)
                       VALUES (?,?,?)
                       ON CONFLICT(lista_id, producto_id) DO UPDATE SET precio=excluded.precio""",
                    (lista_id, r["id"], r["precio"]),
                )
