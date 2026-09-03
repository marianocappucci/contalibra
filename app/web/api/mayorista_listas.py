"""API JSON del add-on mayorista sobre las listas de precio: quiebres por cantidad.

Router aparte del de `listas_precio` (gateado por `listas_precio`) porque su gate
es el del add-on (`require_module("mayorista")`, aplicado en el `include_router`
de web/app.py). Comparte el prefijo `/api/listas-precio`; sus rutas
(`/{id}/items/{pid}/quiebres`, `/{id}/precio`) no chocan con las del router base.

- Los **quiebres** son filas de `item_prices` con `min_quantity` seteado (la fila
  base, `min_quantity IS NULL`, la maneja el editor flat).
- El endpoint `/precio` resuelve el precio efectivo por cantidad vía
  `resolve_price` del motor — lo consume el presupuesto para re-cotizar el
  renglón cuando cambia la cantidad.

Ver `app/db_listas_precio.py` y wiki `distribuidora-mayorista-producto-candidato`.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import database as db

router = APIRouter(prefix="/api/listas-precio", tags=["mayorista"])


class QuiebrePayload(BaseModel):
    min_quantity: float
    amount: float


class QuiebresPayload(BaseModel):
    quiebres: list[QuiebrePayload]


@router.get("/{lista_id}/items/{producto_id}/quiebres")
def ver_quiebres(lista_id: int, producto_id: int):
    if db.get_lista_precio(lista_id) is None:
        raise HTTPException(404, "lista de precios no encontrada")
    return db.get_quiebres(lista_id, producto_id)


@router.put("/{lista_id}/items/{producto_id}/quiebres")
def guardar_quiebres(lista_id: int, producto_id: int, payload: QuiebresPayload):
    if db.get_lista_precio(lista_id) is None:
        raise HTTPException(404, "lista de precios no encontrada")
    vistos: set[float] = set()
    for q in payload.quiebres:
        # La cantidad mínima 1 es el precio base (fila `min_quantity IS NULL`);
        # un quiebre es para MÁS de una unidad.
        if q.min_quantity < 2:
            raise HTTPException(422, "la cantidad mínima de un quiebre tiene que ser 2 o más")
        if q.amount <= 0:
            raise HTTPException(422, "el precio de un quiebre tiene que ser mayor a 0")
        if q.min_quantity in vistos:
            raise HTTPException(422, f"hay dos quiebres con la misma cantidad mínima ({q.min_quantity:g})")
        vistos.add(q.min_quantity)
    db.set_quiebres(
        lista_id, producto_id,
        [{"min_quantity": q.min_quantity, "amount": q.amount} for q in payload.quiebres],
    )
    return db.get_quiebres(lista_id, producto_id)


@router.get("/{lista_id}/precio")
def precio_por_cantidad(lista_id: int, producto_id: int, cantidad: float = 1):
    """El precio efectivo del producto en la lista para esa cantidad (base +
    quiebres). `precio: null` si el producto no tiene precio en la lista."""
    return {"precio": db.resolver_precio_por_cantidad(lista_id, producto_id, cantidad)}
