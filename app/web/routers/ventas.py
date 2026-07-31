
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, JSONResponse

from app import database as db
from app import config_manager
from app import mp_api
from app.web.auth import require_auth

router = APIRouter()
Auth = Annotated[str, Depends(require_auth)]

# Las paginas Jinja2 de este router (list/nueva/detail/anular) se
# removieron en el corte de la migracion a React -- ver
# wiki/entities/contalibra.md, Etapa D. Quedan el flujo de QR dinamico de
# MercadoPago y las descargas de ticket/recibo, que la SPA nueva
# (web/api/ventas.py) linkea/consume directo -- el QR en vivo todavia no
# esta cableado en la SPA (ver nota de alcance en Ventas.tsx), pero el
# endpoint sigue disponible para cuando se construya esa pantalla.


@router.post("/ventas/{vid}/mp-qr")
async def venta_mp_qr(vid: int, user: Auth):
    """Crea una orden QR Dinámico en MP para esta venta y devuelve el QR como data-URL."""
    venta = db.get_venta(vid)
    if not venta:
        raise HTTPException(404)

    cfg = config_manager.load()
    access_token = cfg.get("mp_access_token", "")
    pos_id       = cfg.get("mp_pos_id", "")

    if not access_token or not pos_id:
        raise HTTPException(400, detail="Configurá el Access Token y el POS ID de MercadoPago en Configuración → Integraciones.")

    external_ref = f"venta-{vid}"
    titulo = f"Venta {venta['numero']}"

    try:
        resultado = await mp_api.crear_orden_qr(
            user_id=cfg.get("mp_user_id", ""),
            pos_id=pos_id,
            access_token=access_token,
            external_reference=external_ref,
            titulo=titulo,
            items=venta["items"],
            total=venta["total"],
        )
    except RuntimeError as e:
        raise HTTPException(502, detail=str(e))

    order_id = resultado.get("in_store_order_id", external_ref)
    db.set_venta_mp_order(vid, order_id)

    qr_data = resultado.get("qr_data", "")
    return JSONResponse({"ok": True, "qr_data": qr_data, "order_id": order_id})


@router.get("/ventas/{vid}/mp-status")
async def venta_mp_status(vid: int, user: Auth):
    """Consulta si el pago QR de esta venta ya fue aprobado."""
    venta = db.get_venta(vid)
    if not venta:
        raise HTTPException(404)

    if venta.get("mp_payment_id"):
        return JSONResponse({"status": "approved", "payment_id": venta["mp_payment_id"]})

    cfg = config_manager.load()
    access_token = cfg.get("mp_access_token", "")
    if not access_token:
        raise HTTPException(400, detail="Access Token de MP no configurado.")

    try:
        pago = await mp_api.buscar_pago_por_referencia(f"venta-{vid}", access_token)
    except Exception as e:
        raise HTTPException(502, detail=str(e))

    if not pago:
        return JSONResponse({"status": "pending"})

    status = pago.get("status", "pending")
    if status == "approved":
        payment_id = str(pago["id"])
        db.set_venta_mp_payment(vid, payment_id)
        db.add_venta_pago_referencia_mp(vid, payment_id)
        return JSONResponse({"status": "approved", "payment_id": payment_id})

    return JSONResponse({"status": status})


@router.get("/ventas/{vid}/ticket")
def venta_ticket(vid: int, user: Auth):
    from app import ticket_generator
    venta = db.get_venta(vid)
    if not venta:
        raise HTTPException(404)
    pdf_bytes = ticket_generator.generar_ticket_venta(venta)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="ticket_venta_{vid}.pdf"'},
    )


@router.get("/ventas/{vid}/recibo")
def venta_recibo(vid: int, user: Auth):
    from app import pdf_generator as pg
    venta = db.get_venta(vid)
    if not venta:
        raise HTTPException(404)
    factura_like = {
        "tipo":            None,
        "punto_venta":     0,
        "numero":          venta["id"],
        "fecha":           venta.get("fecha", ""),
        "cliente_razon":   venta.get("cliente_nombre") or "Consumidor Final",
        "cliente_cuit":    venta.get("cliente_cuit", ""),
        "cliente_domicilio": "",
        "total":           venta.get("total", 0),
        "_es_venta":       True,
        "_venta_numero":   venta.get("numero", venta["id"]),
    }
    cobros = [
        {
            "fecha":      venta.get("fecha", ""),
            "medio_pago": p.get("medio", ""),
            "referencia": p.get("referencia", ""),
            "monto":      float(p.get("monto", 0)),
        }
        for p in venta.get("pagos", [])
    ]
    pdf_bytes = pg.generate_pdf_recibo(factura_like, cobros)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_venta_{vid}.pdf"'},
    )
