"""API JSON del add-on mayorista: la lista de precios asignada a un cliente.

Router aparte del de `clientes` a propósito: su gate es el del add-on
(`require_module("mayorista")`, aplicado en el `include_router` de web/app.py),
no el de `clientes`. Los endpoints van bajo `/api/clientes/{id}` para quedar al
lado del resto de la ficha del cliente. Ver `app/db_mayorista.py` y
`plans.py::ADDONS`.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import database as db
from app import db_mayorista
from app.db_listas_precio import get_lista_precio

router = APIRouter(prefix="/api/clientes", tags=["mayorista"])


class ListaDeClientePayload(BaseModel):
    #: `None` limpia la asignación (el cliente vuelve a cotizar con el precio base).
    lista_id: int | None


def _respuesta(lista_id: int | None) -> dict:
    return {
        "lista_id": lista_id,
        "lista": get_lista_precio(lista_id) if lista_id is not None else None,
    }


@router.get("/{cliente_id}/lista-precio")
def obtener_lista_de_cliente(cliente_id: int):
    if not db.get_client(cliente_id):
        raise HTTPException(404, "cliente no encontrado")
    return _respuesta(db_mayorista.get_lista_de_cliente(cliente_id))


@router.put("/{cliente_id}/lista-precio")
def asignar_lista_de_cliente(cliente_id: int, payload: ListaDeClientePayload):
    if not db.get_client(cliente_id):
        raise HTTPException(404, "cliente no encontrado")
    if payload.lista_id is None:
        db_mayorista.quitar_lista_de_cliente(cliente_id)
        return _respuesta(None)
    # La lista tiene que existir: sin este chequeo, la FK lo rechazaría con un
    # 500 opaco en vez de un 422 que dice qué pasó.
    if get_lista_precio(payload.lista_id) is None:
        raise HTTPException(422, "la lista de precios no existe")
    db_mayorista.set_lista_de_cliente(cliente_id, payload.lista_id)
    return _respuesta(payload.lista_id)
