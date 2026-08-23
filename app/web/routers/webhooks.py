"""El webhook de MercadoPago de Contalibra.

El mecanismo —firma, no creerle al cuerpo, contestar 200, idempotencia— vive en
`libracore.mp_webhook` desde el 2026-08-23. Acá quedan **las dos reglas que son
de este producto** y que el motor no tiene por qué conocer:

1. Un pago con `external_reference` `venta-123` es el cobro por QR de una venta
   presencial, no una suscripción: se aplica a esa venta.
2. Un cobro cuya descripción empieza con *"Hosting Mensual"* se factura solo
   aunque el cliente no tenga la bandera `auto_facturar`. Es el negocio de
   hosting de esta empresa, no un concepto de la familia.
"""
import logging

from app import venta_facturacion
from app import database as db
from libracore.mp_webhook import build_mp_webhook_router

logger = logging.getLogger(__name__)


async def _cobro_de_venta_por_qr(
    venta_id: int, payment_id: str, pago: dict, cfg: dict
) -> int | None:
    """Aplica a la venta el cobro que entró por su QR.

    El motor sólo llama acá cuando el pago está **aprobado**, así que no hace
    falta volver a chequearlo.

    ⚠️ El `payment_id` llega por parámetro y **no** se saca de `pago["id"]`: el
    que vale es el de la notificación que se está procesando, que es el que
    sella la idempotencia y el que se guarda en `mp_pagos`. En producción
    coinciden, pero la API no garantiza que el detalle eche el mismo id — y un
    test de este repo cazó justamente eso.

    Devuelve el id de la factura si se emitió, o `None`. Emitir es idempotente
    (`facturar_venta` devuelve la factura existente), así que un reintento de
    MercadoPago no duplica el comprobante.
    """
    db.set_venta_mp_payment(venta_id, payment_id)
    db.add_venta_pago_referencia_mp(venta_id, payment_id)
    logger.info("Venta %s pagada via QR de MercadoPago, payment_id=%s", venta_id, payment_id)

    # 🔴 Hasta el 2026-08-19 acá se retornaba directo y la venta cobrada por QR
    # no se facturaba por ningún camino.
    if not cfg.get("mp_auto_facturar_ventas"):
        return None
    factura = await venta_facturacion.facturar_venta(venta_id)
    logger.info(
        "Auto-factura de la venta %s: id=%s CAE=%s",
        venta_id, factura["id"], factura.get("cae") or "sin CAE",
    )
    return factura["id"]


def _es_hosting_mensual(client: dict, contexto: dict) -> bool:
    """Cuándo se factura solo, en este producto.

    La bandera del cliente **o** que el cobro sea del hosting mensual. La
    segunda mitad es de acá: es el servicio que esta empresa vende y cobra
    todos los meses por MercadoPago.
    """
    if client.get("auto_facturar"):
        return True
    return contexto["descripcion"].lower().startswith("hosting mensual")


router = build_mp_webhook_router(
    manejadores_de_referencia={"venta-": _cobro_de_venta_por_qr},
    debe_auto_facturar=_es_hosting_mensual,
)
