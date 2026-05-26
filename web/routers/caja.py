import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from typing import Annotated
import datetime

import database as db
from web.auth import require_auth
from web.templates_config import templates

router = APIRouter()

Auth = Annotated[str, Depends(require_auth)]


def _periodo_actual():
    hoy = datetime.date.today()
    return hoy.replace(day=1).isoformat(), hoy.isoformat()


@router.get("/caja")
def caja_list(request: Request, user: Auth, desde: str = "", hasta: str = ""):
    if not desde or not hasta:
        desde, hasta = _periodo_actual()
    movimientos = db.get_caja_movimientos(desde, hasta)
    resumen     = db.get_caja_resumen(desde, hasta)
    return templates.TemplateResponse(request, "caja/list.html", {
        "movimientos": movimientos,
        "resumen":     resumen,
        "desde":       desde,
        "hasta":       hasta,
        "active":      "caja",
    })


@router.get("/caja/nuevo")
def caja_nuevo_get(request: Request, user: Auth,
                   tipo: str = "ingreso", monto: str = "",
                   concepto: str = "", factura_id: str = ""):
    return templates.TemplateResponse(request, "caja/form.html", {
        "active":     "caja",
        "error":      None,
        "tipo":       tipo,
        "monto":      monto,
        "concepto":   concepto,
        "factura_id": factura_id,
    })


@router.post("/caja/nuevo")
async def caja_nuevo_post(request: Request, user: Auth):
    form = await request.form()
    try:
        fecha      = str(form.get("fecha", "")).strip()
        tipo       = str(form.get("tipo", "ingreso")).strip()
        concepto   = str(form.get("concepto", "")).strip()
        monto_str  = str(form.get("monto", "")).strip().replace(",", ".")
        referencia = str(form.get("referencia", "")).strip()
        factura_id = form.get("factura_id")
        factura_id = int(factura_id) if factura_id else None

        if not fecha:
            raise ValueError("La fecha es requerida.")
        if not concepto:
            raise ValueError("El concepto es requerido.")
        monto = float(monto_str)
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a cero.")
        if tipo not in ("ingreso", "egreso"):
            raise ValueError("Tipo inválido.")

        db.create_caja_movimiento(fecha, tipo, concepto, monto, referencia, factura_id)

        # Si viene de una factura, volver a su detalle
        if factura_id:
            return RedirectResponse(f"/facturas/{factura_id}", status_code=303)
        return RedirectResponse("/caja", status_code=303)

    except Exception as e:
        return templates.TemplateResponse(request, "caja/form.html", {
            "active": "caja", "error": str(e),
            "tipo": form.get("tipo", "ingreso"),
            "monto": form.get("monto", ""),
            "concepto": form.get("concepto", ""),
            "factura_id": form.get("factura_id", ""),
        }, status_code=422)


@router.post("/caja/{mov_id}/eliminar")
def caja_eliminar(mov_id: int, user: Auth):
    db.delete_caja_movimiento(mov_id)
    return RedirectResponse("/caja", status_code=303)
