"""La sucursal única de Contalibra («Casa central»): lo que el producto aporta al sustrato de sucursales del motor.

Contalibra es de un solo local, pero el motor (`libracommerce`) ya sabe de sucursales: el depósito pertenece a una,
la venta anota la del depósito del que sale, la caja (`cajas.sucursal_id`, de LibraCore) también. Hasta v0.62.0 todo
eso quedaba en NULL. Esto las junta en **una** sucursal predeterminada, para que el día que un cliente pida
multisucursal (F2 del plan, `wiki/analyses/plan-sucursales-contalibra-2026-10-16.md`) no haya que migrar datos con el
cliente mirando. **Nada visible cambia** con una sola sucursal: ninguna pantalla ni ruta de sucursales se monta
(`/api/sucursales` sigue sin existir) y el kit sólo ofrece sucursal con dos o más.

La lógica de fondo es del motor (ADR-063 de libracommerce): `catalogo.adoptar_sucursal_unica` y
`catalogo.completar_sucursal_de_ventas`. Acá queda lo propio del producto: el nombre, las cajas (que son de
LibraCore, no del motor comercial) y el camino de vuelta.

**La misma función en las dos puntas**, como el resto de las tablas propias de la cadena: la revisión de Alembic
`0006_sucursal_unica` (el deploy de una instancia que ya existe) y `init_db()` (el alta de una instancia nueva y cada
reinicio) llaman a `adoptar`. Una instancia nueva y una vieja convergen por el mismo camino, y correrla dos veces no
hace nada la segunda.
"""
from __future__ import annotations

from typing import Any

#: El nombre de la sucursal única (decisión del humano, 2026-10-16).
NOMBRE = "Casa central"


def adoptar(conn: Any) -> dict:
    """Deja la instancia con su sucursal única y devuelve un informe de lo que hizo (todo en cero si no había nada).

    1. La sucursal predeterminada «Casa central» (la crea si no hay ninguna) y todos los depósitos bajo ella.
    2. Las cajas sin sucursal pasan a ella. Una caja que ya tiene una no se toca.
    3. Las ventas de antes se completan con la sucursal de su depósito, con el criterio de `erp.margen`.

    No commitea: es del caller. Serializada entre procesos por el candado del motor (va primero)."""
    from libracommerce.erp import catalogo

    sucursales_antes = conn.execute("SELECT COUNT(*) FROM branches").fetchone()[0]
    huerfanos_antes = conn.execute("SELECT COUNT(*) FROM locations WHERE branch_id IS NULL").fetchone()[0]
    sucursal_id = catalogo.adoptar_sucursal_unica(conn, NOMBRE)
    cajas = conn.execute("UPDATE cajas SET sucursal_id = ? WHERE sucursal_id IS NULL", (sucursal_id,)).rowcount or 0
    ventas = catalogo.completar_sucursal_de_ventas(conn)
    return {
        "sucursal_id": sucursal_id,
        "sucursal_creada": sucursales_antes == 0,
        "depositos_asignados": huerfanos_antes,
        "cajas_asignadas": cajas,
        "ventas_completadas": ventas,
    }


def desadoptar(conn: Any) -> dict:
    """El camino de vuelta de `adoptar` (el `downgrade` de la revisión `0006`): deja en NULL todo lo que apuntaba a la
    sucursal única y la borra.

    🔴 **Sólo si es la que `adoptar` creó, y se identifica por la forma que dejó**: la ÚNICA sucursal de la instancia,
    la predeterminada, con el nombre `NOMBRE`. Si hay más de una (se activó multisucursal después), o la única fue
    renombrada o no es la predeterminada, ya no es «la de la migración»: no se toca nada y se dice por qué
    (`RuntimeError`). Tampoco se baja si algún precio (`item_prices`) u orden de compra (`purchase_orders`) apunta a
    ella: dejarlos en NULL volvería general un precio que es de una sucursal, y borrarla dejaría la referencia colgando.

    Sin sucursales, no hace nada (una base que nunca la adoptó)."""
    filas = conn.execute("SELECT id, name, is_default FROM branches ORDER BY id").fetchall()
    if not filas:
        return {"sucursal_id": None, "depositos": 0, "cajas": 0, "ventas": 0}
    if len(filas) != 1 or not filas[0][2] or filas[0][1] != NOMBRE:
        raise RuntimeError(
            f"No se puede deshacer la sucursal única: la instancia no tiene sólo «{NOMBRE}» como sucursal "
            f"predeterminada (hay {len(filas)}: {[(f[0], f[1]) for f in filas]}). Con más sucursales, o con una "
            "renombrada, deshacerlo borraría datos que ya no son de la migración."
        )
    sucursal_id = filas[0][0]
    for tabla in ("item_prices", "purchase_orders"):
        n = conn.execute(f"SELECT COUNT(*) FROM {tabla} WHERE branch_id = ?", (sucursal_id,)).fetchone()[0]
        if n:
            raise RuntimeError(
                f"No se puede deshacer la sucursal única: {n} fila(s) de {tabla} apuntan a ella "
                f"(branch_id={sucursal_id}). Dejarlas sin sucursal cambiaría lo que significan."
            )
    informe = {"sucursal_id": sucursal_id}
    for clave, sql in (
        ("depositos", "UPDATE locations SET branch_id = NULL WHERE branch_id = ?"),
        ("cajas", "UPDATE cajas SET sucursal_id = NULL WHERE sucursal_id = ?"),
        ("ventas", "UPDATE sales SET branch_id = NULL WHERE branch_id = ?"),
    ):
        informe[clave] = conn.execute(sql, (sucursal_id,)).rowcount or 0
    conn.execute("DELETE FROM branches WHERE id = ?", (sucursal_id,))
    return informe
