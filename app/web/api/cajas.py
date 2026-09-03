"""API JSON de Cajas (configuracion de puntos de cobro) para la SPA (ver
wiki/entities/contalibra.md, migracion a React). Reusa `db_caja.py` (via
`database.py`) tal cual -- ver web/api/clientes.py para el patron general
de esta etapa. `GET /cajas/{id}/medios` (usado por el POS de ventas)
sigue en `web/routers/cajas.py` sin tocar, se reusa desde la SPA cuando
se migre Ventas."""
from fastapi import APIRouter, HTTPException
from libracore import medios_pago
from pydantic import BaseModel

from app import database as db

router = APIRouter(prefix="/api/cajas", tags=["cajas"])

# 🔴 Del motor, no de una copia escrita acá. Ésta y la de `api/ventas.py` eran
# **la misma lista escrita dos veces en el mismo repo**, byte a byte — y otras
# 26 copias vivían en los demás productos, ya divergiendo entre sí. Ver
# `libracore.medios_pago` y `wiki/concepts/medios-de-pago-familia-libra.md`.
TODOS_MEDIOS = medios_pago.para_selector()


class CajaPayload(BaseModel):
    nombre: str
    descripcion: str = ""
    medios_pago: list[str] = []


class CajaUpdatePayload(CajaPayload):
    activo: bool = True


@router.get("")
def listar():
    return db.get_all_cajas()


@router.get("/medios-disponibles")
def medios_disponibles():
    return TODOS_MEDIOS


@router.post("")
def crear(payload: CajaPayload):
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(422, "El nombre es obligatorio.")
    cid = db.create_caja_config(nombre, payload.descripcion.strip(), payload.medios_pago)
    return db.get_caja_config(cid)


@router.put("/{cid}")
def actualizar(cid: int, payload: CajaUpdatePayload):
    if not db.get_caja_config(cid):
        raise HTTPException(404, "Caja no encontrada")
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(422, "El nombre es obligatorio.")
    db.update_caja_config(cid, nombre, payload.descripcion.strip(), payload.medios_pago, 1 if payload.activo else 0)
    return db.get_caja_config(cid)


@router.post("/{cid}/set-default")
def set_default(cid: int):
    if not db.get_caja_config(cid):
        raise HTTPException(404, "Caja no encontrada")
    db.set_default_caja(cid)
    return db.get_caja_config(cid)


@router.delete("/{cid}")
def eliminar(cid: int):
    if not db.get_caja_config(cid):
        raise HTTPException(404, "Caja no encontrada")
    try:
        db.delete_caja_config(cid)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"ok": True}
