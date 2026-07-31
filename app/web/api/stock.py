"""API JSON de Stock para la SPA (ver wiki/entities/contalibra.md,
migracion a React). Reusa `db_stock.py` (via `database.py`) tal cual --
ver web/api/clientes.py para el patron general de esta etapa."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import database as db
from app.web.api_auth import get_current_user_json

router = APIRouter(prefix="/api/stock", tags=["stock"])

TIPO_LABELS = {"entrada": "Entrada", "salida": "Salida", "ajuste": "Ajuste", "venta": "Venta"}


class AjustePayload(BaseModel):
    modo: str = "absoluto"  # absoluto | entrada | salida
    cantidad: float
    referencia: str = ""
    fecha: str = ""


@router.get("")
def listar():
    productos = db.get_stock_todos()
    alertas = [p for p in productos if p["stock_actual"] <= p["stock_minimo"] and p["stock_minimo"] > 0]
    return {"productos": productos, "alertas": alertas}


@router.get("/movimientos")
def movimientos(producto_id: int = 0, desde: str = "", hasta: str = ""):
    return db.get_movimientos_stock(producto_id=producto_id or None, desde=desde, hasta=hasta)


@router.get("/{pid}")
def actual(pid: int):
    if not db.get_producto(pid):
        raise HTTPException(404, "Producto no encontrado")
    return {"stock_actual": db.get_stock_actual(pid)}


@router.post("/{pid}/ajuste")
def ajustar(pid: int, payload: AjustePayload, user: dict = Depends(get_current_user_json)):
    if not db.get_producto(pid):
        raise HTTPException(404, "Producto no encontrado")
    fecha = payload.fecha or date.today().isoformat()
    referencia = payload.referencia.strip() or "Ajuste manual"

    if payload.modo == "absoluto":
        db.ajustar_stock(pid, payload.cantidad, referencia, usuario_id=user["id"], fecha=fecha)
    elif payload.modo == "entrada":
        db.add_movimiento_stock(pid, "entrada", abs(payload.cantidad), referencia, usuario_id=user["id"], fecha=fecha)
    elif payload.modo == "salida":
        db.add_movimiento_stock(pid, "salida", -abs(payload.cantidad), referencia, usuario_id=user["id"], fecha=fecha)
    else:
        raise HTTPException(422, "Modo inválido.")

    return {"stock_actual": db.get_stock_actual(pid)}
