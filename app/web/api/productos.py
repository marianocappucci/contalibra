"""API JSON de Productos para la SPA (ver wiki/entities/contalibra.md,
migracion a React). Reusa `db_productos.py` (via `database.py`) tal cual
-- ver web/api/clientes.py para el patron general de esta etapa. El
autocompletado usado por Ventas/Facturas (`GET /productos/buscar`) queda
sin tocar hasta que se migren esos modulos (Etapa C)."""
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import database as db

router = APIRouter(prefix="/api/productos", tags=["productos"])

UNIDADES = ["u", "kg", "g", "lt", "ml", "m", "cm", "m²", "caja", "par", "docena", "pack"]


class ProductoPayload(BaseModel):
    nombre: str
    codigo: str = ""
    descripcion: str = ""
    precio_venta: float = 0
    precio_costo: float = 0
    unidad: str = "u"
    categoria: str = ""
    stock_minimo: float = 0
    activo: bool = True
    tipo: Literal["producto", "servicio"] = "producto"


@router.get("")
def listar(q: str = ""):
    return db.get_all_productos(q=q)


@router.get("/categorias")
def listar_categorias():
    return db.get_categorias_producto()


class CategoriaPayload(BaseModel):
    nombre: str


@router.post("/categorias")
def crear_categoria(payload: CategoriaPayload):
    """Faltaba -- el tab "Categorías" de Config (frontend/src/pages/Config.tsx,
    CategoriasTab) ya llamaba a este endpoint para el lado de productos, pero
    nunca se habia expuesto aca (el router viejo lo tenia en
    web/routers/config.py -> POST /config/categorias-producto). Ver auditoria
    de campo por campo, modulo Listas de precio/Egresos/Usuarios/Config."""
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(422, "El nombre es obligatorio.")
    db.create_categoria_producto(nombre)
    return db.get_categorias_producto()


@router.delete("/categorias/{cid}")
def eliminar_categoria(cid: int):
    db.delete_categoria_producto(cid)
    return db.get_categorias_producto()


@router.post("")
def crear(payload: ProductoPayload):
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(422, "El nombre es obligatorio.")
    try:
        pid = db.create_producto(
            nombre=nombre, codigo=payload.codigo.strip(),
            descripcion=payload.descripcion.strip(),
            precio_venta=payload.precio_venta, precio_costo=payload.precio_costo,
            unidad=payload.unidad, categoria=payload.categoria.strip(),
            stock_minimo=payload.stock_minimo, tipo=payload.tipo,
        )
    except Exception as e:
        raise HTTPException(422, str(e))
    return db.get_producto(pid)


@router.put("/{pid}")
def actualizar(pid: int, payload: ProductoPayload):
    if not db.get_producto(pid):
        raise HTTPException(404, "Producto no encontrado")
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(422, "El nombre es obligatorio.")
    try:
        db.update_producto(
            pid=pid, nombre=nombre, codigo=payload.codigo.strip(),
            descripcion=payload.descripcion.strip(),
            precio_venta=payload.precio_venta, precio_costo=payload.precio_costo,
            unidad=payload.unidad, categoria=payload.categoria.strip(),
            activo=1 if payload.activo else 0, stock_minimo=payload.stock_minimo,
            tipo=payload.tipo,
        )
    except Exception as e:
        raise HTTPException(422, str(e))
    return db.get_producto(pid)


@router.delete("/{pid}")
def eliminar(pid: int):
    if not db.get_producto(pid):
        raise HTTPException(404, "Producto no encontrado")
    db.delete_producto(pid)
    return {"ok": True}
