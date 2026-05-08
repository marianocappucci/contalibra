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

TIPOS = [
    {"value": 1, "label": "Factura A"},
    {"value": 6, "label": "Factura B"},
]

CONCEPTOS = [
    {"value": 1, "label": "Productos"},
    {"value": 2, "label": "Servicios"},
    {"value": 3, "label": "Productos y Servicios"},
]

IVA_CODES = {
    "Responsable Inscripto": 1,
    "IVA Responsable Inscripto": 1,
    "Monotributista": 6,
    "Responsable Monotributo": 6,
    "IVA Exento": 4,
    "Consumidor Final": 5,
    "No Alcanzado": 3,
    "IVA No Responsable": 3,
}


def _arca_punto_venta():
    configs = db.obtener_todas_arca_configs()
    return configs[0].get("punto_venta", 1) if configs else 1


@router.get("/facturas")
def facturas_list(request: Request, user: Auth, q: str = ""):
    items = db.search_facturas(q) if q else db.get_all_facturas(200)
    return templates.TemplateResponse(request, "facturas/list.html", {
        "facturas": items, "q": q, "active": "facturas",
    })


@router.get("/facturas/nueva")
def factura_nueva_get(request: Request, user: Auth):
    return templates.TemplateResponse(request, "facturas/form.html", {
        "clientes": db.get_all_clients(),
        "tipos": TIPOS,
        "conceptos": CONCEPTOS,
        "punto_venta": _arca_punto_venta(),
        "active": "facturas",
        "factura": None,
        "error": None,
    })


@router.post("/facturas/nueva")
async def factura_nueva_post(request: Request, user: Auth):
    form = await request.form()
    clientes = db.get_all_clients()

    try:
        tipo        = int(form.get("tipo", 6))
        punto_venta = int(form.get("punto_venta", 1) or 1)
        concepto    = int(form.get("concepto", 1))
        fecha_str   = str(form.get("fecha", "")).strip()
        observations = str(form.get("observations", "")).strip()
        tax_rate    = float(form.get("tax_rate", "0.21"))

        client_id      = int(form.get("client_id", 0)) or None
        client_name    = str(form.get("client_name", "")).strip()
        client_cuit    = str(form.get("client_cuit", "")).strip()
        client_address = str(form.get("client_address", "")).strip()
        client_iva     = str(form.get("client_iva", "")).strip()

        descs  = form.getlist("desc[]")
        qtys   = form.getlist("qty[]")
        prices = form.getlist("price[]")

        if not client_name:
            raise ValueError("El nombre/razón social del cliente es requerido.")
        if not any(d.strip() for d in descs):
            raise ValueError("Debe agregar al menos un ítem.")

        if client_id:
            c = db.get_client(client_id)
            if c:
                client_name    = c["name"]
                client_cuit    = c.get("cuit_dni", "")
                client_address = c.get("address", "")
                client_iva     = c.get("iva_condition", "")

        items = []
        for desc, qty_s, price_s in zip(descs, qtys, prices):
            if not desc.strip():
                continue
            qty   = float(qty_s.replace(",", "."))
            price = float(price_s.replace(",", "."))
            items.append({
                "description": desc.strip(),
                "qty": qty,
                "unit_price": price,
                "subtotal": round(qty * price, 2),
            })

        if not items:
            raise ValueError("Debe agregar al menos un ítem válido.")

        subtotal   = round(sum(i["subtotal"] for i in items), 2)
        iva_amount = round(subtotal * tax_rate, 2)
        total      = round(subtotal + iva_amount, 2)
        numero     = db.get_next_factura_numero(punto_venta, tipo)
        iva_code   = IVA_CODES.get(client_iva, 0)

        factura_id = db.create_factura(
            tipo=tipo, punto_venta=punto_venta, numero=numero,
            fecha=fecha_str, cliente_cuit=client_cuit,
            cliente_razon=client_name, cliente_iva_cond=iva_code,
            items=items, subtotal=subtotal, iva_amount=iva_amount,
            total=total, concepto=concepto, observaciones=observations,
            cliente_domicilio=client_address,
        )
        factura = db.get_factura(factura_id)
        pdf_path = pdf_gen.generate_pdf_factura(factura)
        db.update_factura_pdf_path(factura_id, pdf_path)
        return RedirectResponse(f"/facturas/{factura_id}", status_code=303)

    except Exception as e:
        return templates.TemplateResponse(request, "facturas/form.html", {
            "clientes": clientes, "tipos": TIPOS, "conceptos": CONCEPTOS,
            "punto_venta": _arca_punto_venta(),
            "active": "facturas", "factura": None, "error": str(e),
        }, status_code=422)


@router.get("/facturas/{factura_id}")
def factura_detail(request: Request, factura_id: int, user: Auth):
    factura = db.get_factura(factura_id)
    if not factura:
        raise HTTPException(404)
    from pdf_generator import _TIPO_LABELS, _CONCEPTO_LABELS, _IVA_LABELS
    return templates.TemplateResponse(request, "facturas/detail.html", {
        "factura": factura,
        "tipo_label":    _TIPO_LABELS.get(factura["tipo"], "Documento"),
        "concepto_label": _CONCEPTO_LABELS.get(factura.get("concepto", 1), "Productos"),
        "iva_label":     _IVA_LABELS.get(factura.get("cliente_iva_cond") or 0, ""),
        "active": "facturas",
    })


@router.get("/facturas/{factura_id}/pdf")
def factura_pdf(factura_id: int, user: Auth):
    factura = db.get_factura(factura_id)
    if not factura:
        raise HTTPException(404)
    pdf_path = pdf_gen.generate_pdf_factura(factura)
    db.update_factura_pdf_path(factura_id, pdf_path)
    pv  = str(factura["punto_venta"]).zfill(4)
    num = str(factura["numero"]).zfill(8)
    return FileResponse(pdf_path, media_type="application/pdf",
                        filename=f"factura_{pv}_{num}.pdf")


@router.post("/facturas/{factura_id}/eliminar")
def factura_eliminar(factura_id: int, user: Auth):
    db.delete_factura(factura_id)
    return RedirectResponse("/facturas", status_code=303)
