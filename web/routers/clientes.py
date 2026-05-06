import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

import database as db
from web.auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

Auth = Annotated[str, Depends(require_auth)]


@router.get("/clientes")
def clientes_list(request: Request, user: Auth):
    return templates.TemplateResponse(request, "clientes/list.html", {
        "clientes": db.get_all_clients(), "active": "clientes",
    })


@router.get("/clientes/nuevo")
def cliente_nuevo_get(request: Request, user: Auth):
    return templates.TemplateResponse(request, "clientes/form.html", {
        "cliente": None, "error": None, "active": "clientes",
    })


@router.post("/clientes/nuevo")
async def cliente_nuevo_post(request: Request, user: Auth):
    form = await request.form()
    name = str(form.get("name", "")).strip()
    if not name:
        return templates.TemplateResponse(request, "clientes/form.html", {
            "cliente": None, "error": "El nombre es obligatorio.", "active": "clientes",
        }, status_code=422)
    db.create_client(
        name,
        str(form.get("address", "")).strip(),
        str(form.get("cuit_dni", "")).strip(),
        str(form.get("email", "")).strip(),
        str(form.get("phone", "")).strip(),
    )
    return RedirectResponse("/clientes", status_code=303)


@router.get("/clientes/{cliente_id}/editar")
def cliente_editar_get(request: Request, cliente_id: int, user: Auth):
    cliente = db.get_client(cliente_id)
    if not cliente:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "clientes/form.html", {
        "cliente": cliente, "error": None, "active": "clientes",
    })


@router.post("/clientes/{cliente_id}/editar")
async def cliente_editar_post(request: Request, cliente_id: int, user: Auth):
    cliente = db.get_client(cliente_id)
    if not cliente:
        raise HTTPException(404)
    form = await request.form()
    name = str(form.get("name", "")).strip()
    if not name:
        return templates.TemplateResponse(request, "clientes/form.html", {
            "cliente": cliente, "error": "El nombre es obligatorio.", "active": "clientes",
        }, status_code=422)
    db.update_client(
        cliente_id,
        name=name,
        address=str(form.get("address", "")).strip(),
        cuit_dni=str(form.get("cuit_dni", "")).strip(),
        email=str(form.get("email", "")).strip(),
        phone=str(form.get("phone", "")).strip(),
    )
    return RedirectResponse("/clientes", status_code=303)


@router.post("/clientes/{cliente_id}/eliminar")
def cliente_eliminar(request: Request, cliente_id: int, user: Auth):
    try:
        db.delete_client(cliente_id)
    except ValueError as e:
        return templates.TemplateResponse(request, "clientes/list.html", {
            "clientes": db.get_all_clients(), "error": str(e), "active": "clientes",
        }, status_code=422)
    return RedirectResponse("/clientes", status_code=303)
