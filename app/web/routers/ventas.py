
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, JSONResponse

import logging

from app import database as db
from app import config_manager
from app import mp_api
from app import venta_facturacion
from app.web.auth import require_auth
from libracore.pdf_generator import generate_pdf_recibo_doc
from libracore.recibos import SinCobros

logger = logging.getLogger(__name__)
router = APIRouter()
Auth = Annotated[str, Depends(require_auth)]


def _usuario_id(username: str):
    """`require_auth` devuelve el username, no el usuario — ver la nota igual
    en `routers/facturas.py`."""
    usuario = db.get_usuario_by_username(username)
    return usuario["id"] if usuario else None

# Las paginas Jinja2 de este router (list/nueva/detail/anular) se
# removieron en el corte de la migracion a React -- ver
# wiki/entities/contalibra.md, Etapa D. Quedan el flujo de QR de MercadoPago
# y las descargas de ticket/recibo, que la SPA nueva (web/api/ventas.py)
# linkea/consume directo.
#
# El QR quedo sin cablear en la SPA desde ese corte hasta el 2026-08-19: el
# endpoint existia y no lo llamaba nadie, asi que elegir "Mercado Pago" como
# medio de pago registraba el medio sin cobrar nada. Ahora lo llama el boton
# "Cobrar con QR" de VentaDetalle.tsx.


@router.post("/ventas/{vid}/mp-qr")
async def venta_mp_qr(vid: int, user: Auth):
    """Pone el monto de esta venta a cobrar en el QR de la caja.

    No devuelve ninguna imagen: es el modelo de **QR fijo por punto de venta**,
    o sea el cartel impreso del mostrador, que no cambia nunca. Lo que cambia es
    cuánto cobra cuando alguien lo escanea. Ver `libracore.mp_api.crear_orden_qr`.
    """
    venta = db.get_venta(vid)
    if not venta:
        raise HTTPException(404)

    cfg = config_manager.load()
    access_token = cfg.get("mp_access_token", "")
    pos_id       = cfg.get("mp_pos_id", "")
    user_id      = cfg.get("mp_user_id", "")

    if not access_token or not pos_id or not user_id:
        raise HTTPException(400, detail="Configurá el Access Token, el User ID y el POS ID de MercadoPago en Configuración → Integraciones.")

    external_ref = f"venta-{vid}"
    titulo = f"Venta {venta['numero']}"

    try:
        resultado = await mp_api.crear_orden_qr(
            user_id=user_id,
            pos_id=pos_id,
            access_token=access_token,
            external_reference=external_ref,
            titulo=titulo,
            items=venta["items"],
            total=venta["total"],
        )
    except RuntimeError as e:
        raise HTTPException(502, detail=str(e))

    # MercadoPago contesta 204 sin cuerpo, así que `resultado` viene vacío: la
    # referencia externa es el único identificador que queda de esta orden, y
    # alcanza porque es la misma con la que vuelve el pago en el webhook.
    order_id = resultado.get("in_store_order_id", external_ref)
    db.set_venta_mp_order(vid, order_id)

    # Se devolvía también `qr_data`, que en este modelo no existe: el QR es el
    # cartel impreso de la caja y no hay imagen que mandar.
    return JSONResponse({"ok": True, "order_id": order_id})


async def _facturar_si_corresponde(vid: int, cfg: dict) -> int | None:
    """Emite la factura de la venta si la instancia tiene la automática prendida.

    Existe porque hay **dos** caminos por los que se entera de que el QR se
    pagó —el webhook de MercadoPago y este poll— y hasta el 2026-08-20 sólo el
    primero facturaba. En la instancia real el webhook **no llegaba nunca** (0
    POST a `/webhooks/mercadopago` en el log, contra 5 a `mp-qr`), así que el
    único camino vivo era justamente el que no emitía: la venta quedaba cobrada
    y "Sin facturar".

    No propaga el error: el cobro ya está registrado, y perderlo sería peor que
    quedarse sin la factura, que se puede emitir con el botón del detalle.
    """
    if not cfg.get("mp_auto_facturar_ventas"):
        return None
    try:
        factura = await venta_facturacion.facturar_venta(vid)
    except Exception as e:
        logger.error("Error auto-facturando venta %s: %s", vid, e)
        return None
    logger.info("Auto-factura de venta %s: id=%s CAE=%s",
                vid, factura["id"], factura.get("cae") or "sin CAE")
    return factura["id"]


@router.get("/ventas/{vid}/mp-status")
async def venta_mp_status(vid: int, user: Auth):
    """Consulta si el pago QR de esta venta ya fue aprobado.

    Es un GET con efectos: sella la referencia del pago y, si corresponde, emite
    la factura. Emitir es idempotente (`facturar_venta` devuelve la que ya
    exista), así que el poll pegándole cada 3 segundos no duplica nada.
    """
    venta = db.get_venta(vid)
    if not venta:
        raise HTTPException(404)

    if venta.get("mp_payment_id"):
        # Ya estaba acreditada. Se intenta facturar igual: cubre a las que se
        # acreditaron antes de que existiera esto, y a las que fallaron al
        # emitir la primera vez.
        factura_id = venta.get("factura_id") or await _facturar_si_corresponde(
            vid, config_manager.load()
        )
        return JSONResponse({
            "status": "approved",
            "payment_id": venta["mp_payment_id"],
            "factura_id": factura_id,
        })

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
        factura_id = await _facturar_si_corresponde(vid, cfg)
        return JSONResponse({
            "status": "approved",
            "payment_id": payment_id,
            "factura_id": factura_id,
        })

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
    """El recibo de una venta, como **documento numerado**.

    Este link lo arman `Ventas.tsx` y `VentaDetalle.tsx`, así que no se puede
    mover: lo que cambia es lo que devuelve. Se fue con el cambio todo el
    armado del `factura_like` — el motor sabe leer una venta directamente, y
    esa traducción a mano era la que hacía falta cuando el PDF se generaba al
    vuelo desde una factura.
    """
    try:
        recibo = db.emitir_recibo_venta(vid, usuario_id=_usuario_id(user))
    except SinCobros as exc:
        raise HTTPException(404, detail=str(exc))
    pv  = str(recibo["punto_venta"]).zfill(4)
    num = str(recibo["numero"]).zfill(8)
    return Response(
        content=generate_pdf_recibo_doc(recibo),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_{pv}-{num}.pdf"'},
    )
