"""API JSON de Listas de precio para la SPA (ver
wiki/entities/contalibra.md, migracion a React). Reusa `db_listas_precio.py`
(via `database.py`) tal cual -- ver web/api/clientes.py para el patron
general de esta etapa.

Nota: el `GET /api/listas-precio/{id}/precios` que ya usa `ventas/nueva.html`
(autocompletado del POS) sigue viviendo en `web/routers/listas_precio.py`
sin tocar -- se reusa desde la SPA cuando se migre Ventas (Etapa C). El
listado general viejo (`GET /api/listas-precio`, sin uso real) se removio
de ese router porque colisionaba con el de aca.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import database as db

router = APIRouter(prefix="/api/listas-precio", tags=["listas_precio"])


class ListaPrecioPayload(BaseModel):
    nombre: str
    descripcion: str = ""


class ListaPrecioUpdatePayload(BaseModel):
    nombre: str
    descripcion: str = ""
    activa: bool = True


class ItemsPayload(BaseModel):
    precios: dict[int, float]


class AjustePorcentualPayload(BaseModel):
    porcentaje: float
    base: str = "lista"
    categoria: str = ""


class ImportarPayload(BaseModel):
    fuente: str
    fuente_lista_id: int | None = None


@router.get("")
def listar():
    return db.get_all_listas_precio()


@router.post("")
def crear(payload: ListaPrecioPayload):
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(422, "El nombre es obligatorio.")
    lista_id = db.create_lista_precio(nombre, payload.descripcion.strip())
    return db.get_lista_precio(lista_id)


@router.put("/{lista_id}")
def actualizar(lista_id: int, payload: ListaPrecioUpdatePayload):
    if not db.get_lista_precio(lista_id):
        raise HTTPException(404, "Lista de precio no encontrada")
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(422, "El nombre es obligatorio.")
    db.update_lista_precio(lista_id, nombre, payload.descripcion.strip(), 1 if payload.activa else 0)
    return db.get_lista_precio(lista_id)


@router.delete("/{lista_id}")
def eliminar(lista_id: int):
    if not db.get_lista_precio(lista_id):
        raise HTTPException(404, "Lista de precio no encontrada")
    db.delete_lista_precio(lista_id)
    return {"ok": True}


@router.get("/{lista_id}/items")
def items(lista_id: int, categoria: str = ""):
    if not db.get_lista_precio(lista_id):
        raise HTTPException(404, "Lista de precio no encontrada")
    return db.get_lista_precio_items(lista_id, categoria)


@router.put("/{lista_id}/items")
def guardar_items(lista_id: int, payload: ItemsPayload):
    if not db.get_lista_precio(lista_id):
        raise HTTPException(404, "Lista de precio no encontrada")
    db.save_lista_precio_items(lista_id, payload.precios)
    return db.get_lista_precio_items(lista_id)


@router.post("/{lista_id}/ajuste-porcentual")
def ajuste_porcentual(lista_id: int, payload: AjustePorcentualPayload):
    if not db.get_lista_precio(lista_id):
        raise HTTPException(404, "Lista de precio no encontrada")
    actualizados = db.apply_porcentaje_lista(lista_id, payload.porcentaje, payload.base, payload.categoria)
    return {"actualizados": actualizados}


@router.post("/{lista_id}/importar")
def importar(lista_id: int, payload: ImportarPayload):
    if not db.get_lista_precio(lista_id):
        raise HTTPException(404, "Lista de precio no encontrada")
    db.importar_precios_lista(lista_id, payload.fuente, payload.fuente_lista_id)
    return db.get_lista_precio_items(lista_id)
