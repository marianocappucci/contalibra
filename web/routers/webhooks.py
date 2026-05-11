import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import hashlib
import hmac
import json
import datetime
import calendar
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import database as db
import config_manager
import mp_api
import email_sender
import pdf_generator as pdf_gen
import arca_wsaa
import arca_wsfe

logger = logging.getLogger(__name__)
router = APIRouter()

_TIPO_POR_CONDICION = {
    "Monotributista":        11,
    "IVA Exento":            6,
    "Responsable Inscripto": 6,
}
_TIPO_LABEL = {
    1: "Factura A", 6: "Factura B", 11: "Factura C",
}


def _verificar_firma(body: bytes, x_signature: str, x_request_id: str,
                     payment_id: str, secret: str) -> bool:
    ts = v1 = ""
    for part in x_signature.split(","):
        if part.startswith("ts="):
            ts = part[3:]
        elif part.startswith("v1="):
            v1 = part[3:]
    if not ts or not v1:
        return False
    template = f"id:{payment_id};request-id:{x_request_id};ts:{ts}"
    expected = hmac.new(secret.encode(), template.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


def _service_dates_for_current_month():
    today = datetime.date.today()
    first = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    last = today.replace(day=last_day)
    return first.isoformat(), last.isoformat(), today.isoformat()


@router.post("/webhooks/mercadopago", include_in_schema=False)
async def webhook_mercadopago(request: Request):
    body = await request.body()
    cfg = config_manager.load()

    access_token = cfg.get("mp_access_token", "")
    webhook_secret = cfg.get("mp_webhook_secret", "")

    if not access_token:
        logger.warning("MercadoPago webhook recibido pero access_token no configurado.")
        return JSONResponse({"ok": False, "error": "not configured"}, status_code=200)

    try:
        payload = json.loads(body)
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)

    event_type = payload.get("type", "")
    if event_type != "payment":
        return JSONResponse({"ok": True, "msg": "ignored"}, status_code=200)

    payment_id = str(payload.get("data", {}).get("id", ""))
    if not payment_id:
        return JSONResponse({"ok": False, "error": "no payment id"}, status_code=400)

    # Verificar firma HMAC (solo loguea si falla — no bloquea)
    x_signature = request.headers.get("x-signature", "")
    if webhook_secret and x_signature:
        x_request_id = request.headers.get("x-request-id", "")
        if not _verificar_firma(body, x_signature, x_request_id, payment_id, webhook_secret):
            logger.warning("Firma MercadoPago no coincide para payment %s — procesando igual", payment_id)

    # Idempotencia
    if db.get_mp_pago(payment_id):
        return JSONResponse({"ok": True, "msg": "already processed"}, status_code=200)

    # Obtener detalle del pago
    try:
        pago = await mp_api.obtener_pago(payment_id, access_token)
    except Exception as e:
        logger.error("Error obteniendo pago %s de MP: %s", payment_id, e)
        # Devolvemos 200 para que MP no reintente; el error queda en los logs
        return JSONResponse({"ok": False, "error": str(e)}, status_code=200)

    status = pago.get("status", "")
    if status != "approved":
        db.create_mp_pago(
            mp_payment_id=payment_id, status=status,
            monto=pago.get("transaction_amount", 0),
            payer_email=pago.get("payer", {}).get("email", ""),
            payer_name="", factura_id=None,
        )
        return JSONResponse({"ok": True, "msg": f"status={status}, skipped"}, status_code=200)

    monto       = float(pago.get("transaction_amount", 0))
    payer       = pago.get("payer", {})
    payer_email = payer.get("email", "")
    payer_name  = (
        f"{payer.get('first_name', '')} {payer.get('last_name', '')}".strip()
        or payer_email
    )

    # Buscar o crear cliente
    client = db.get_client_by_email(payer_email) if payer_email else None
    if not client:
        client_id = db.create_client(
            name=payer_name or payer_email,
            email=payer_email,
            iva_condition="Consumidor Final",
        )
        client = db.get_client(client_id)
    else:
        client_id = client["id"]

    # Determinar tipo de comprobante
    iva_cond = cfg.get("empresa_iva_condition", "Monotributista")
    tipo = _TIPO_POR_CONDICION.get(iva_cond, 11)

    # Importes
    try:
        iva_rate = float(cfg.get("mp_iva_rate", "0") or "0")
    except ValueError:
        iva_rate = 0.0

    if tipo == 11 or iva_rate == 0:
        subtotal   = round(monto, 2)
        iva_amount = 0.0
        total      = round(monto, 2)
    else:
        subtotal   = round(monto / (1 + iva_rate), 2)
        iva_amount = round(monto - subtotal, 2)
        total      = round(monto, 2)

    descripcion = cfg.get("mp_concepto_descripcion", "Suscripcion mensual") or "Suscripcion mensual"
    items = [{
        "description": descripcion,
        "qty": 1,
        "unit_price": subtotal,
        "subtotal": subtotal,
    }]

    fecha_hoy = datetime.date.today().isoformat()
    fch_desde, fch_hasta, fch_vto = _service_dates_for_current_month()

    # Obtener config ARCA y número de comprobante
    arca_cfg = db.obtener_todas_arca_configs()
    arca     = arca_cfg[0] if arca_cfg else None
    ta       = None
    punto_venta = arca["punto_venta"] if arca else 1

    if arca and arca.get("certificado_path") and arca.get("clave_path"):
        try:
            ta = await arca_wsaa.autenticar(
                arca["certificado_path"], arca["clave_path"], arca["ambiente"]
            )
            ultimo = await arca_wsfe.ultimo_numero_autorizado(
                punto_venta, tipo, arca["cuit"],
                ta["token"], ta["sign"], arca["ambiente"],
            )
            numero = ultimo + 1
        except Exception as e:
            logger.error("ARCA auth error en webhook: %s", e)
            ta     = None
            numero = db.get_next_factura_numero(punto_venta, tipo)
    else:
        numero = db.get_next_factura_numero(punto_venta, tipo)

    # IVA code del receptor
    iva_code_receptor = 5  # Consumidor Final por defecto

    factura_id = db.create_factura(
        tipo=tipo, punto_venta=punto_venta, numero=numero,
        fecha=fecha_hoy,
        cliente_cuit=client.get("cuit_dni", ""),
        cliente_razon=client["name"],
        cliente_iva_cond=iva_code_receptor,
        items=items,
        subtotal=subtotal,
        iva_amount=iva_amount,
        total=total,
        concepto=2,  # Servicios
        observaciones=f"Pago MercadoPago #{payment_id}",
        cliente_domicilio=client.get("address", ""),
        fch_serv_desde=fch_desde,
        fch_serv_hasta=fch_hasta,
        fch_vto_pago=fch_vto,
    )
    factura = db.get_factura(factura_id)

    # Solicitar CAE
    if ta and arca:
        try:
            cae_data = await arca_wsfe.solicitar_cae(
                factura, arca["cuit"], ta["token"], ta["sign"], arca["ambiente"]
            )
            db.update_factura_cae(factura_id, cae_data["cae"], cae_data["cae_vto"])
            factura = db.get_factura(factura_id)
        except Exception as e:
            logger.error("Error obteniendo CAE para factura %s: %s", factura_id, e)

    # Generar PDF
    try:
        pdf_path = pdf_gen.generate_pdf_factura(factura)
        db.update_factura_pdf_path(factura_id, pdf_path)
        factura = db.get_factura(factura_id)
    except Exception as e:
        logger.error("Error generando PDF factura %s: %s", factura_id, e)
        pdf_path = None

    # Registrar en caja
    pv_str  = str(punto_venta).zfill(4)
    num_str = str(numero).zfill(8)
    tipo_lb = _TIPO_LABEL.get(tipo, "Factura")
    db.create_caja_movimiento(
        fecha=fecha_hoy,
        tipo="ingreso",
        concepto=f"Cobro {tipo_lb} {pv_str}-{num_str} — {client['name']} (MP)",
        monto=total,
        referencia=f"MP#{payment_id}",
        factura_id=factura_id,
    )

    # Registrar pago MP (idempotencia)
    db.create_mp_pago(
        mp_payment_id=payment_id, status="approved",
        monto=monto, payer_email=payer_email,
        payer_name=payer_name, factura_id=factura_id,
    )

    # Enviar email si está configurado y hay PDF
    smtp_host = cfg.get("email_smtp_host", "")
    smtp_user = cfg.get("email_smtp_user", "")
    smtp_pass = cfg.get("email_smtp_password", "")
    from_email = cfg.get("email_from", "")

    if smtp_host and smtp_user and smtp_pass and from_email and payer_email and pdf_path:
        try:
            email_sender.enviar_comprobante(
                to_email=payer_email,
                to_name=payer_name,
                pdf_path=pdf_path,
                empresa_nombre=cfg.get("empresa_nombre", ""),
                factura_label=f"{tipo_lb} {pv_str}-{num_str}",
                total=total,
                smtp_host=smtp_host,
                smtp_port=int(cfg.get("email_smtp_port", "587") or "587"),
                smtp_user=smtp_user,
                smtp_password=smtp_pass,
                from_email=from_email,
                from_name=cfg.get("email_from_name", ""),
            )
            logger.info("Email enviado a %s para factura %s", payer_email, factura_id)
        except Exception as e:
            logger.error("Error enviando email a %s: %s", payer_email, e)

    return JSONResponse({
        "ok": True,
        "factura_id": factura_id,
        "numero": f"{pv_str}-{num_str}",
    }, status_code=200)
