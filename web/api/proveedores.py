"""API JSON de Proveedores para la SPA (ver wiki/entities/contalibra.md,
migracion a React). Reusa `db_egresos.py` (via `database.py`) tal cual --
ver web/api/clientes.py para el patron general de esta etapa. El detalle
con egresos asociados queda para cuando se migre el modulo Egresos."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import database as db

router = APIRouter(prefix="/api/proveedores", tags=["proveedores"])


class ProveedorPayload(BaseModel):
    nombre: str
    cuit_dni: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    iva_condition: str = ""


@router.get("")
def listar(q: str = ""):
    return db.search_proveedores(q) if q else db.get_all_proveedores()


@router.post("")
def crear(payload: ProveedorPayload):
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(422, "El nombre es obligatorio.")
    pid = db.create_proveedor(
        nombre=nombre, cuit_dni=payload.cuit_dni.strip(), email=payload.email.strip(),
        phone=payload.phone.strip(), address=payload.address.strip(),
        iva_condition=payload.iva_condition.strip(),
    )
    return db.get_proveedor(pid)


@router.put("/{pid}")
def actualizar(pid: int, payload: ProveedorPayload):
    if not db.get_proveedor(pid):
        raise HTTPException(404, "Proveedor no encontrado")
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(422, "El nombre es obligatorio.")
    db.update_proveedor(
        pid, nombre=nombre, cuit_dni=payload.cuit_dni.strip(), email=payload.email.strip(),
        phone=payload.phone.strip(), address=payload.address.strip(),
        iva_condition=payload.iva_condition.strip(),
    )
    return db.get_proveedor(pid)


@router.delete("/{pid}")
def eliminar(pid: int):
    if not db.get_proveedor(pid):
        raise HTTPException(404, "Proveedor no encontrado")
    try:
        db.delete_proveedor(pid)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"ok": True}
