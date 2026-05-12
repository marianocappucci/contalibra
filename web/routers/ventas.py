import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from typing import Annotated
from datetime import date
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

import database as db
from web.auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
Auth = Annotated[str, Depends(require_auth)]

MEDIOS_PAGO = [
    {"id": "efectivo",      "label": "Efectivo",        "icon": "bi-cash"},
    {"id": "transferencia", "label": "Transferencia",   "icon": "bi-bank"},
    {"id": "mercadopago",   "label": "Mercado Pago",    "icon": "bi-phone"},
    {"id": "cuenta_dni",    "label": "Cuenta DNI",      "icon": "bi-person-vcard"},
    {"id": "billetera",     "label": "Otras billeteras","icon": "bi-wallet2"},
]

MEDIO_LABELS = {m["id"]: m["label"] for m in MEDIOS_PAGO}


@router.get("/ventas")
def ventas_list(request: Request, user: Auth,
                desde: str = "", hasta: str = "", q: str = ""):
    ventas = db.get_all_ventas(desde=desde, hasta=hasta, q=q)
    return templates.TemplateResponse(request, "ventas/list.html", {
        "ventas": ventas, "desde": desde, "hasta": hasta, "q": q,
        "active": "ventas", "medio_labels": MEDIO_LABELS,
    })


@router.get("/ventas/nueva")
def venta_nueva_get(request: Request, user: Auth):
    clientes = db.get_all_clients()
    return templates.TemplateResponse(request, "ventas/nueva.html", {
        "clientes": clientes, "medios_pago": MEDIOS_PAGO,
        "hoy": date.today().isoformat(), "active": "ventas",
        "error": None,
    })


@router.post("/ventas/nueva")
async def venta_nueva_post(request: Request, user: Auth):
    form = await request.form()

    # — items —
    nombres   = form.getlist("item_nombre")
    qtys      = form.getlist("item_qty")
    precios   = form.getlist("item_precio")
    prod_ids  = form.getlist("item_producto_id")

    items = []
    for nombre, qty_s, precio_s, pid_s in zip(nombres, qtys, precios, prod_ids):
        nombre = nombre.strip()
        if not nombre:
            continue
        try:
            qty    = float(qty_s.replace(",", "."))
            precio = float(precio_s.replace(",", "."))
        except ValueError:
            continue
        items.append({
            "nombre":      nombre,
            "qty":         qty,
            "precio":      precio,
            "subtotal":    round(qty * precio, 2),
            "producto_id": int(pid_s) if pid_s else None,
        })

    if not items:
        clientes = db.get_all_clients()
        return templates.TemplateResponse(request, "ventas/nueva.html", {
            "clientes": clientes, "medios_pago": MEDIOS_PAGO,
            "hoy": date.today().isoformat(), "active": "ventas",
            "error": "Debe agregar al menos un ítem.",
        }, status_code=422)

    subtotal  = round(sum(i["subtotal"] for i in items), 2)
    descuento = round(float(form.get("descuento") or 0), 2)
    total     = round(subtotal - descuento, 2)

    # — pagos —
    pagos = []
    for m in MEDIOS_PAGO:
        monto_s = str(form.get(f"pago_{m['id']}", "")).strip()
        ref     = str(form.get(f"ref_{m['id']}", "")).strip()
        if monto_s:
            try:
                monto = float(monto_s.replace(",", "."))
                if monto > 0:
                    pagos.append({"medio": m["id"], "monto": monto, "referencia": ref})
            except ValueError:
                pass

    total_pagado = round(sum(p["monto"] for p in pagos), 2)
    if not pagos:
        clientes = db.get_all_clients()
        return templates.TemplateResponse(request, "ventas/nueva.html", {
            "clientes": clientes, "medios_pago": MEDIOS_PAGO,
            "hoy": date.today().isoformat(), "active": "ventas",
            "error": "Debe registrar al menos un medio de pago.",
        }, status_code=422)

    # — cliente —
    cliente_id_s = str(form.get("cliente_id", "")).strip()
    cliente_id   = int(cliente_id_s) if cliente_id_s else None
    cliente_nombre = str(form.get("cliente_nombre", "")).strip()
    if cliente_id:
        c = db.get_client(cliente_id)
        if c:
            cliente_nombre = c["name"]

    fecha = str(form.get("fecha", date.today().isoformat()))
    obs   = str(form.get("observaciones", "")).strip()

    # — usuario actual —
    usuario = db.get_usuario_by_username(user)
    usuario_id = usuario["id"] if usuario else None

    numero = db.get_next_venta_numero()

    # — guardar —
    venta_id = db.create_venta(
        numero=numero, fecha=fecha, items=items,
        subtotal=subtotal, descuento=descuento, total=total,
        cliente_id=cliente_id, cliente_nombre=cliente_nombre,
        usuario_id=usuario_id, observaciones=obs,
    )
    for p in pagos:
        db.add_venta_pago(venta_id, p["medio"], p["monto"], p.get("referencia", ""))

    # — movimiento de caja por cada medio —
    medio_map = {m["id"]: m["label"] for m in MEDIOS_PAGO}
    for p in pagos:
        label = medio_map.get(p["medio"], p["medio"].title())
        db.create_caja_movimiento(
            fecha=fecha,
            tipo="ingreso",
            concepto=f"Venta {numero} — {label}",
            monto=p["monto"],
            referencia=p.get("referencia", ""),
        )

    # — descuento de stock (si el módulo está activo) —
    mods = db.get_modulos()
    if mods.get("stock"):
        db.descontar_stock_venta(venta_id, items, fecha=fecha, usuario_id=usuario_id)

    # — vincular al turno activo del usuario —
    if usuario_id:
        turno = db.get_turno_activo(usuario_id)
        if turno:
            db.vincular_venta_turno(venta_id, turno["id"])

    return RedirectResponse(f"/ventas/{venta_id}", status_code=303)


@router.get("/ventas/{vid}")
def venta_detail(request: Request, vid: int, user: Auth):
    venta = db.get_venta(vid)
    if not venta:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "ventas/detail.html", {
        "venta": venta, "active": "ventas",
        "medio_labels": MEDIO_LABELS,
    })


@router.post("/ventas/{vid}/anular")
def venta_anular(request: Request, vid: int, user: Auth):
    venta = db.get_venta(vid)
    if not venta:
        raise HTTPException(404)
    db.anular_venta(vid)
    return RedirectResponse(f"/ventas/{vid}", status_code=303)
