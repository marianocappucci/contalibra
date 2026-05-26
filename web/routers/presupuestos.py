import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from typing import Annotated

import database as db
import pdf_generator as pdf_gen
import config_manager
import email_sender
from web.auth import require_auth
from web.templates_config import templates, _moneda

router = APIRouter()

Auth = Annotated[str, Depends(require_auth)]


@router.get("/presupuestos")
def presupuestos_list(request: Request, user: Auth, q: str = ""):
    items = db.search_presupuestos(q) if q else db.get_all_presupuestos(200)
    return templates.TemplateResponse(request, "presupuestos/list.html", {
        "presupuestos": items, "q": q, "active": "presupuestos",
    })


@router.get("/presupuestos/nuevo")
def presupuesto_nuevo_get(request: Request, user: Auth):
    return templates.TemplateResponse(request, "presupuestos/form.html", {
        "clientes": db.get_all_clients(), "active": "presupuestos",
        "presupuesto": None, "error": None,
    })


@router.post("/presupuestos/nuevo")
async def presupuesto_nuevo_post(request: Request, user: Auth):
    form = await request.form()
    clientes = db.get_all_clients()

    try:
        client_id = int(form.get("client_id", 0)) or None
        client_name = str(form.get("client_name", "")).strip()
        client_address = str(form.get("client_address", "")).strip()
        client_cuit = str(form.get("client_cuit", "")).strip()
        client_email = str(form.get("client_email", "")).strip()
        client_phone = str(form.get("client_phone", "")).strip()
        date_str = str(form.get("date", "")).strip()
        valid_until = str(form.get("valid_until", "")).strip()
        tax_rate = float(form.get("tax_rate", "0.21"))
        observations = str(form.get("observations", "")).strip()

        descs = form.getlist("desc[]")
        qtys = form.getlist("qty[]")
        prices = form.getlist("price[]")

        if not client_name:
            raise ValueError("El nombre del cliente es requerido.")
        if not any(d.strip() for d in descs):
            raise ValueError("Debe agregar al menos un ítem.")

        items = []
        for desc, qty_s, price_s in zip(descs, qtys, prices):
            if not desc.strip():
                continue
            qty = float(qty_s.replace(",", "."))
            price = float(price_s.replace(",", "."))
            items.append({"description": desc.strip(), "qty": qty,
                          "unit_price": price, "subtotal": round(qty * price, 2)})

        if not items:
            raise ValueError("Debe agregar al menos un ítem válido.")

        if client_id:
            c = db.get_client(client_id)
            if c:
                client_name = c["name"]
                client_address = c.get("address", "")
                client_cuit = c.get("cuit_dni", "")
                client_email = c.get("email", "")
                client_phone = c.get("phone", "")

        subtotal = round(sum(i["subtotal"] for i in items), 2)
        tax_amount = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax_amount, 2)
        number = db.get_next_presupuesto_number()

        pres_id = db.create_presupuesto(
            number=number, date=date_str, valid_until=valid_until,
            client_id=client_id, client_name=client_name,
            client_address=client_address, client_cuit=client_cuit,
            client_email=client_email, client_phone=client_phone,
            items=items, subtotal=subtotal,
            tax_rate=tax_rate, tax_amount=tax_amount,
            total=total, observations=observations,
        )
        pdf_path = pdf_gen.generate_pdf_presupuesto(db.get_presupuesto(pres_id))
        db.update_presupuesto_pdf_path(pres_id, pdf_path)
        return RedirectResponse(f"/presupuestos/{pres_id}", status_code=303)

    except Exception as e:
        return templates.TemplateResponse(request, "presupuestos/form.html", {
            "clientes": clientes, "active": "presupuestos",
            "presupuesto": None, "error": str(e),
        }, status_code=422)


@router.get("/presupuestos/{pres_id}")
def presupuesto_detail(request: Request, pres_id: int, user: Auth):
    pres = db.get_presupuesto(pres_id)
    if not pres:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "presupuestos/detail.html", {
        "presupuesto": pres, "active": "presupuestos",
        "email_ok": None, "email_error": None,
    })


@router.post("/presupuestos/{pres_id}/estado")
async def presupuesto_estado(request: Request, pres_id: int, user: Auth):
    form = await request.form()
    estado = str(form.get("estado", ""))
    pres = db.get_presupuesto(pres_id)
    if not pres:
        raise HTTPException(404)

    if estado == "aceptado":
        db.update_presupuesto_status(pres_id, "aceptado")
        if form.get("convertir_remito") == "1":
            _convertir_a_remito(pres)
    elif estado == "rechazado":
        db.update_presupuesto_status(pres_id, "rechazado")

    return RedirectResponse(f"/presupuestos/{pres_id}", status_code=303)


def _convertir_a_remito(presupuesto):
    remito_number = db.get_next_remito_number()
    remito_id = db.create_remito(
        number=remito_number, date=presupuesto["date"],
        client_id=presupuesto["client_id"],
        client_name=presupuesto["client_name"],
        client_address=presupuesto.get("client_address", ""),
        client_cuit=presupuesto.get("client_cuit", ""),
        client_email=presupuesto.get("client_email", ""),
        client_phone=presupuesto.get("client_phone", ""),
        items=presupuesto["items"], subtotal=presupuesto["subtotal"],
        tax_rate=presupuesto["tax_rate"], tax_amount=presupuesto["tax_amount"],
        total=presupuesto["total"], observations=presupuesto.get("observations", ""),
    )
    pdf_path = pdf_gen.generate_pdf(db.get_remito(remito_id))
    db.update_remito_pdf_path(remito_id, pdf_path)
    db.update_presupuesto_remito_id(presupuesto["id"], remito_id)


@router.get("/presupuestos/{pres_id}/pdf")
def presupuesto_pdf(pres_id: int, user: Auth):
    pres = db.get_presupuesto(pres_id)
    if not pres:
        raise HTTPException(404)
    pdf_path = pdf_gen.generate_pdf_presupuesto(pres)
    db.update_presupuesto_pdf_path(pres_id, pdf_path)
    safe = pres["number"].replace("/", "-")
    return FileResponse(pdf_path, media_type="application/pdf",
                        filename=f"presupuesto_{safe}.pdf")


@router.post("/presupuestos/{pres_id}/enviar-email")
async def presupuesto_enviar_email(request: Request, pres_id: int, user: Auth):
    form    = await request.form()
    to_mail = str(form.get("email", "")).strip()
    pres    = db.get_presupuesto(pres_id)
    if not pres:
        raise HTTPException(404)

    cfg = config_manager.load()
    ctx = {"presupuesto": pres, "active": "presupuestos"}

    if not cfg.get("email_smtp_host"):
        return templates.TemplateResponse(request, "presupuestos/detail.html",
            {**ctx, "email_error": "Configurá el servidor SMTP en Configuración → Integraciones.",
             "email_ok": None})

    if not to_mail:
        return templates.TemplateResponse(request, "presupuestos/detail.html",
            {**ctx, "email_error": "Ingresá una dirección de email.", "email_ok": None})

    pdf_path = pres.get("pdf_path") or pdf_gen.generate_pdf_presupuesto(pres)
    doc_label = f"Presupuesto {pres['number']}"

    try:
        email_sender.enviar_comprobante(
            to_email=to_mail, to_name=pres["client_name"],
            pdf_path=pdf_path, empresa_nombre=cfg.get("empresa_nombre", ""),
            factura_label=doc_label, total=pres["total"],
            smtp_host=cfg["email_smtp_host"],
            smtp_port=int(cfg.get("email_smtp_port", 587)),
            smtp_user=cfg["email_smtp_user"],
            smtp_password=cfg.get("email_smtp_password", ""),
            from_email=cfg.get("email_from") or cfg["email_smtp_user"],
            from_name=cfg.get("email_from_name", ""),
            asunto=f"{doc_label} — {cfg.get('empresa_nombre', '')}",
            cuerpo=(
                f"Estimado/a {pres['client_name']},\n\n"
                f"Adjuntamos el presupuesto solicitado.\n\n"
                f"Número: {pres['number']}\n"
                f"Total: $ {_moneda(pres['total'])}\n"
                f"Válido hasta: {pres['valid_until']}\n\n"
                f"Muchas gracias.\n{cfg.get('empresa_nombre', '')}"
            ),
        )
        return templates.TemplateResponse(request, "presupuestos/detail.html",
            {**ctx, "email_ok": f"Email enviado a {to_mail}.", "email_error": None})
    except Exception as e:
        return templates.TemplateResponse(request, "presupuestos/detail.html",
            {**ctx, "email_error": f"Error al enviar: {e}", "email_ok": None})


@router.post("/presupuestos/{pres_id}/eliminar")
def presupuesto_eliminar(pres_id: int, user: Auth):
    db.delete_presupuesto(pres_id)
    return RedirectResponse("/presupuestos", status_code=303)
