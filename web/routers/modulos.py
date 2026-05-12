from typing import Annotated
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import database as db
from web.auth import require_admin

router = APIRouter()
Auth = Annotated[dict, Depends(require_admin)]

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

_PLANES = ["basico", "estandar", "premium"]

_LABELS = {
    "clientes":     "Clientes",
    "caja":         "Caja",
    "ventas":       "Ventas",
    "facturacion":  "Facturación",
    "remitos":      "Remitos",
    "presupuestos": "Presupuestos",
    "productos":    "Productos",
    "stock":        "Stock",
}

_PLAN_LABELS = {
    "basico":   "Básico",
    "estandar": "Estándar",
    "premium":  "Premium",
}


@router.get("/config/modulos")
def modulos_get(request: Request, user: Auth, saved: str = ""):
    modulos = db.get_modulos_completo()
    for m in modulos:
        m["label"] = _LABELS.get(m["modulo"], m["modulo"].title())
        m["plan_label"] = _PLAN_LABELS.get(m["plan"], m["plan"].title())
    return templates.TemplateResponse(request, "config/modulos.html", {
        "modulos": modulos,
        "planes": _PLANES,
        "plan_labels": _PLAN_LABELS,
        "active": "config",
        "saved": saved,
    })


@router.post("/config/modulos/toggle/{modulo}")
def modulo_toggle(modulo: str, request: Request, user: Auth):
    mods = db.get_modulos()
    if modulo in mods:
        db.set_modulo(modulo, not mods[modulo])
    return RedirectResponse("/config/modulos?saved=1", status_code=303)


@router.post("/config/modulos/plan/{plan}")
def modulos_apply_plan(plan: str, request: Request, user: Auth):
    if plan in _PLANES:
        db.apply_plan(plan)
    return RedirectResponse("/config/modulos?saved=1", status_code=303)
