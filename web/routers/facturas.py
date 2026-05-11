import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

import database as db
import pdf_generator as pdf_gen
import arca_wsaa
import arca_wsfe
import config_manager
from web.auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

Auth = Annotated[str, Depends(require_auth)]

_TIPOS_POR_CONDICION = {
    "Responsable Inscripto": [
        {"value": 1, "label": "Factura A"},
        {"value": 6, "label": "Factura B"},
    ],
    "IVA Exento": [
        {"value": 6, "label": "Factura B"},
    ],
    "Monotributista": [
        {"value": 11, "label": "Factura C"},
    ],
}
_TIPOS_DEFAULT = _TIPOS_POR_CONDICION["Monotributista"]


def _tipos_emisor():
    cfg = config_manager.load()
    cond = cfg.get("empresa_iva_condition", "Monotributista")
    return _TIPOS_POR_CONDICION.get(cond, _TIPOS_DEFAULT)


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
    tipos = _tipos_emisor()
    es_monotributista = len(tipos) == 1 and tipos[0]["value"] == 11
    return templates.TemplateResponse(request, "facturas/form.html", {
        "clientes": db.get_all_clients(),
        "tipos": tipos,
        "conceptos": CONCEPTOS,
        "punto_venta": _arca_punto_venta(),
        "active": "facturas",
        "factura": None,
        "error": None,
        "es_monotributista": es_monotributista,
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
        # Factura C (monotributista) nunca discrimina IVA
        tax_rate    = 0.0 if tipo == 11 else float(form.get("tax_rate", "0.21"))

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
        iva_code   = IVA_CODES.get(client_iva, 0)

        # Obtener configuración ARCA y autenticar
        arca_cfg = db.obtener_todas_arca_configs()
        arca     = arca_cfg[0] if arca_cfg else None
        ta       = None

        if arca and arca.get("certificado_path") and arca.get("clave_path"):
            try:
                ta = await arca_wsaa.autenticar(
                    arca["certificado_path"], arca["clave_path"], arca["ambiente"]
                )
                # Número correlativo según ARCA (no la DB local)
                ultimo = await arca_wsfe.ultimo_numero_autorizado(
                    punto_venta, tipo, arca["cuit"],
                    ta["token"], ta["sign"], arca["ambiente"],
                )
                numero = ultimo + 1
            except Exception:
                ta     = None
                numero = db.get_next_factura_numero(punto_venta, tipo)
        else:
            numero = db.get_next_factura_numero(punto_venta, tipo)

        factura_id = db.create_factura(
            tipo=tipo, punto_venta=punto_venta, numero=numero,
            fecha=fecha_str, cliente_cuit=client_cuit,
            cliente_razon=client_name, cliente_iva_cond=iva_code,
            items=items, subtotal=subtotal, iva_amount=iva_amount,
            total=total, concepto=concepto, observaciones=observations,
            cliente_domicilio=client_address,
        )
        factura = db.get_factura(factura_id)

        # Solicitar CAE si tenemos token válido
        if ta and arca:
            try:
                cae_data = await arca_wsfe.solicitar_cae(
                    factura, arca["cuit"], ta["token"], ta["sign"], arca["ambiente"]
                )
                db.update_factura_cae(factura_id, cae_data["cae"], cae_data["cae_vto"])
                factura = db.get_factura(factura_id)
            except Exception:
                pass  # Factura guardada sin CAE; se puede reintentar desde el detalle

        pdf_path = pdf_gen.generate_pdf_factura(factura)
        db.update_factura_pdf_path(factura_id, pdf_path)
        return RedirectResponse(f"/facturas/{factura_id}", status_code=303)

    except Exception as e:
        tipos = _tipos_emisor()
        return templates.TemplateResponse(request, "facturas/form.html", {
            "clientes": clientes, "tipos": tipos, "conceptos": CONCEPTOS,
            "punto_venta": _arca_punto_venta(),
            "active": "facturas", "factura": None, "error": str(e),
            "es_monotributista": len(tipos) == 1 and tipos[0]["value"] == 11,
        }, status_code=422)


def _detail_ctx(factura: dict, error: str = "") -> dict:
    from pdf_generator import _TIPO_LABELS, _CONCEPTO_LABELS, _IVA_LABELS
    return {
        "factura":        factura,
        "tipo_label":     _TIPO_LABELS.get(factura["tipo"], "Documento"),
        "concepto_label": _CONCEPTO_LABELS.get(factura.get("concepto", 1), "Productos"),
        "iva_label":      _IVA_LABELS.get(factura.get("cliente_iva_cond") or 0, ""),
        "active":         "facturas",
        "arca_error":     error,
    }


@router.get("/facturas/{factura_id}")
def factura_detail(request: Request, factura_id: int, user: Auth):
    factura = db.get_factura(factura_id)
    if not factura:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "facturas/detail.html",
                                      _detail_ctx(factura))


@router.post("/facturas/{factura_id}/autorizar")
async def factura_autorizar(request: Request, factura_id: int, user: Auth):
    """Reintenta obtener CAE para una factura pendiente."""
    factura = db.get_factura(factura_id)
    if not factura:
        raise HTTPException(404)

    if factura.get("cae"):
        return RedirectResponse(f"/facturas/{factura_id}", status_code=303)

    arca_cfg = db.obtener_todas_arca_configs()
    arca     = arca_cfg[0] if arca_cfg else None
    if not arca or not arca.get("certificado_path") or not arca.get("clave_path"):
        return templates.TemplateResponse(request, "facturas/detail.html",
            {**_detail_ctx(factura),
             "arca_error": "ARCA no está configurado. Cargá los certificados en Configuración."})

    try:
        ta = await arca_wsaa.autenticar(
            arca["certificado_path"], arca["clave_path"], arca["ambiente"]
        )
        cae_data = await arca_wsfe.solicitar_cae(
            factura, arca["cuit"], ta["token"], ta["sign"], arca["ambiente"]
        )
        db.update_factura_cae(factura_id, cae_data["cae"], cae_data["cae_vto"])
        factura = db.get_factura(factura_id)
        pdf_path = pdf_gen.generate_pdf_factura(factura)
        db.update_factura_pdf_path(factura_id, pdf_path)
        return RedirectResponse(f"/facturas/{factura_id}", status_code=303)

    except Exception as e:
        factura = db.get_factura(factura_id)
        return templates.TemplateResponse(request, "facturas/detail.html",
            {**_detail_ctx(factura), "arca_error": str(e)})


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
