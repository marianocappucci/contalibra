import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

import database as db
import pdf_generator as pdf_gen
from web.auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

Auth = Annotated[str, Depends(require_auth)]


@router.get("/remitos")
def remitos_list(request: Request, user: Auth, q: str = ""):
    items = db.search_remitos(q) if q else db.get_all_remitos(200)
    return templates.TemplateResponse(request, "remitos/list.html", {
        "remitos": items, "q": q, "active": "remitos",
    })


@router.get("/remitos/nuevo")
def remito_nuevo_get(request: Request, user: Auth):
    return templates.TemplateResponse(request, "remitos/form.html", {
        "clientes": db.get_all_clients(), "active": "remitos",
        "remito": None, "error": None,
    })


@router.post("/remitos/nuevo")
async def remito_nuevo_post(request: Request, user: Auth):
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
        number = db.get_next_remito_number()

        remito_id = db.create_remito(
            number=number, date=date_str,
            client_id=client_id, client_name=client_name,
            client_address=client_address, client_cuit=client_cuit,
            client_email=client_email, client_phone=client_phone,
            items=items, subtotal=subtotal,
            tax_rate=tax_rate, tax_amount=tax_amount,
            total=total, observations=observations,
        )
        pdf_path = pdf_gen.generate_pdf(db.get_remito(remito_id))
        db.update_remito_pdf_path(remito_id, pdf_path)
        return RedirectResponse(f"/remitos/{remito_id}", status_code=303)

    except Exception as e:
        return templates.TemplateResponse(request, "remitos/form.html", {
            "clientes": clientes, "active": "remitos",
            "remito": None, "error": str(e),
        }, status_code=422)


@router.get("/remitos/{remito_id}")
def remito_detail(request: Request, remito_id: int, user: Auth):
    remito = db.get_remito(remito_id)
    if not remito:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "remitos/detail.html", {
        "remito": remito, "active": "remitos",
    })


@router.get("/remitos/{remito_id}/pdf")
def remito_pdf(remito_id: int, user: Auth):
    remito = db.get_remito(remito_id)
    if not remito:
        raise HTTPException(404)
    pdf_path = remito.get("pdf_path", "")
    if not pdf_path or not os.path.exists(pdf_path):
        pdf_path = pdf_gen.generate_pdf(remito)
        db.update_remito_pdf_path(remito_id, pdf_path)
    safe = remito["number"].replace("/", "-")
    return FileResponse(pdf_path, media_type="application/pdf",
                        filename=f"remito_{safe}.pdf")


@router.post("/remitos/{remito_id}/eliminar")
def remito_eliminar(remito_id: int, user: Auth):
    db.delete_remito(remito_id)
    return RedirectResponse("/remitos", status_code=303)
