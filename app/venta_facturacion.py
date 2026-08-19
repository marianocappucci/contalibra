"""Facturación de una venta del módulo Ventas — mostrador y QR MercadoPago.

Es el camino que faltaba. Hasta el 2026-08-19 `vincular_venta_factura()` no
tenía ningún call site, así que la pestaña "Facturadas" de Ventas no la podía
llenar nada: ni el botón del detalle (un link al formulario de alta vacío, sin
`venta_id`) ni el webhook de MercadoPago, que ante un pago con
`external_reference = venta-<id>` registraba el cobro contra la venta y
retornaba **antes** del bloque de auto-facturación.

Dos diferencias con `mp_facturacion.generar_factura_mp`, y son la razón por la
que esto no es una llamada a esa función:

1. **No registra movimiento de caja.** La venta ya registró uno por cada medio
   de pago, dentro de la misma transacción que la creó
   (`db_ventas.crear_venta_directa`). Volver a registrarlo duplicaría el ingreso.
2. **No crea un cliente.** Una venta de mostrador sin cliente se factura a
   Consumidor Final sin persistir nada — un buffet con 200 ventas por día
   llenaría `clients` en una semana. `generar_factura_mp` sí lo crea, porque
   ahí el pagador es un cliente real que se factura de nuevo el mes que viene.

Lo demás sí se comparte: la numeración y el CAE salen de `libracore`
(`arca_helper`), igual que el alta manual de `POST /api/facturas`.
"""
import datetime
import logging

from app import config_manager
from app import database as db
from app import pdf_generator as pdf_gen
from app.web.helpers.arca_helper import get_next_numero_with_arca, solicitar_cae

logger = logging.getLogger(__name__)

# Cliente sintético para la venta de mostrador sin cliente asignado. No se
# guarda en `clients`: viaja hasta `create_factura`, que snapshotea razón
# social, CUIT y domicilio en la propia factura.
CONSUMIDOR_FINAL = {
    "name": "Consumidor Final",
    "cuit_dni": "",
    "iva_condition": "Consumidor Final",
    "address": "",
    "email": "",
}

_IVA_CODES = {
    "Responsable Inscripto": 1, "IVA Responsable Inscripto": 1,
    "Monotributista": 6, "Responsable Monotributo": 6,
    "IVA Exento": 4, "Consumidor Final": 5,
    "No Alcanzado": 3, "IVA No Responsable": 3,
}
_TIPO_LABEL = {1: "Factura A", 6: "Factura B", 11: "Factura C"}

# Misma tasa por defecto que el formulario manual (`FacturaPayload.tax_rate`).
IVA_RATE_DEFAULT = 0.21

# Los ids son los de `MEDIOS_PAGO` en `web/api/ventas.py`; los valores, los de
# `CONDICIONES_VENTA` en `web/api/facturas.py` (que es lo que acepta ARCA).
_MEDIO_A_CONDICION = {
    "efectivo": "Contado",
    "transferencia": "Transferencia Bancaria",
    "mercadopago": "Otros medios de pago electrónico",
    "cuenta_dni": "Otros medios de pago electrónico",
    "billetera": "Otros medios de pago electrónico",
    "cuenta_corriente": "Cuenta Corriente",
}


class VentaNoFacturable(Exception):
    """La venta no está en condiciones de emitirse (inexistente o anulada)."""


def _tipo_comprobante(emisor_cond: str, cliente_cond: str) -> int:
    """A/B/C según el emisor, y A sólo si el cliente también es RI.

    Un Monotributista emite siempre C. Un Responsable Inscripto emite A a otro
    RI y B a todo lo demás — que en un mostrador es el caso normal.
    """
    if emisor_cond == "Monotributista":
        return 11
    if cliente_cond in ("Responsable Inscripto", "IVA Responsable Inscripto"):
        return 1
    return 6


def _armar_items(venta: dict, iva_rate: float) -> tuple[list, float, float, float]:
    """Convierte las líneas de la venta en líneas de factura.

    Los precios de una venta son finales (con IVA adentro); los de una factura
    son netos y el IVA se suma aparte. Con `iva_rate > 0` cada línea se
    desagrega, y el IVA del comprobante se calcula como la diferencia contra el
    total de la venta en vez de sumar los IVA línea por línea: así el total de
    la factura coincide **exacto** con lo que ya entró a la caja, sin arrastrar
    el redondeo de cada línea.
    """
    total_venta = round(float(venta["total"]), 2)
    divisor = 1 + iva_rate

    items = []
    for it in venta["items"]:
        neto_linea = round(float(it["subtotal"]) / divisor, 2)
        items.append({
            "description": it["nombre"],
            "qty": float(it["qty"]),
            "unit_price": round(float(it["precio"]) / divisor, 2),
            "subtotal": neto_linea,
        })

    descuento = round(float(venta.get("descuento") or 0), 2)
    if descuento:
        neto_desc = round(descuento / divisor, 2)
        items.append({
            "description": "Descuento",
            "qty": 1,
            "unit_price": -neto_desc,
            "subtotal": -neto_desc,
        })

    subtotal = round(sum(i["subtotal"] for i in items), 2)

    if iva_rate:
        iva_amount = round(total_venta - subtotal, 2)
        total = total_venta
    else:
        # Sin IVA discriminado las líneas ya son el total. Si no coincide con
        # el de la venta, manda la venta: es la plata que está en la caja.
        iva_amount = 0.0
        total = subtotal
        if abs(total - total_venta) > 0.01:
            logger.warning(
                "Venta %s: las líneas suman %.2f y la venta dice %.2f — "
                "se factura por las líneas",
                venta["id"], total, total_venta,
            )

    return items, subtotal, iva_amount, total


def _condicion_venta(venta: dict) -> str:
    pagos = venta.get("pagos") or []
    if len(pagos) == 1:
        return _MEDIO_A_CONDICION.get(pagos[0].get("medio", ""), "Otra")
    if len(pagos) > 1:
        return "Otra"
    return "Contado"


async def facturar_venta(venta_id: int, *, usuario_id: int | None = None) -> dict:
    """Emite la factura de una venta, pide el CAE, genera el PDF y las vincula.

    Idempotente: si la venta ya tiene factura devuelve esa, sin emitir otra. Es
    lo que sostiene el reintento del webhook de MercadoPago, que puede llegar
    más de una vez para el mismo pago.

    No toca la caja — ver el docstring del módulo.
    """
    venta = db.get_venta(venta_id)
    if not venta:
        raise VentaNoFacturable(f"La venta {venta_id} no existe.")

    if venta.get("factura_id"):
        logger.info("Venta %s ya facturada (factura %s), no se reemite",
                    venta_id, venta["factura_id"])
        return db.get_factura(venta["factura_id"])

    if venta.get("status") == "cancelled":
        raise VentaNoFacturable(f"La venta {venta_id} está anulada.")

    cfg = config_manager.load()
    emisor_cond = cfg.get("empresa_iva_condition", "Monotributista")

    cliente = CONSUMIDOR_FINAL
    if venta.get("cliente_id"):
        registrado = db.get_client(venta["cliente_id"])
        if registrado:
            cliente = registrado

    tipo = _tipo_comprobante(emisor_cond, cliente.get("iva_condition", "Consumidor Final"))
    iva_rate = 0.0 if tipo == 11 else IVA_RATE_DEFAULT

    items, subtotal, iva_amount, total = _armar_items(venta, iva_rate)
    if not items:
        raise VentaNoFacturable(f"La venta {venta_id} no tiene ítems.")

    punto_venta = _punto_venta()
    numero, ta, arca = await get_next_numero_with_arca(punto_venta, tipo)

    factura_id = db.create_factura(
        tipo=tipo, punto_venta=punto_venta, numero=numero,
        fecha=datetime.date.today().isoformat(),
        cliente_cuit=cliente.get("cuit_dni", ""),
        cliente_razon=cliente["name"],
        cliente_iva_cond=_IVA_CODES.get(cliente.get("iva_condition", "Consumidor Final"), 5),
        items=items,
        subtotal=subtotal, iva_amount=iva_amount, total=total,
        concepto=1,  # Productos
        observaciones=f"Venta {venta['numero']}",
        condicion_venta=_condicion_venta(venta),
        usuario_id=usuario_id if usuario_id is not None else venta.get("usuario_id"),
    )

    factura = db.get_factura(factura_id)
    factura = await solicitar_cae(factura_id, factura, ta, arca)

    try:
        pdf_path = pdf_gen.generate_pdf_factura(factura)
        db.update_factura_pdf_path(factura_id, pdf_path)
        factura = db.get_factura(factura_id)
    except Exception:
        # El PDF se regenera solo al descargarlo; perderlo no invalida el CAE,
        # y fallar acá dejaría la factura emitida y sin vincular a la venta.
        logger.exception("Error generando el PDF de la factura %s", factura_id)

    db.vincular_venta_factura(venta_id, factura_id)

    logger.info(
        "Venta %s facturada: %s %04d-%08d (CAE %s)",
        venta["numero"], _TIPO_LABEL.get(tipo, "Factura"),
        punto_venta, factura["numero"], factura.get("cae") or "sin CAE",
    )
    return factura


def _punto_venta() -> int:
    configs = db.obtener_todas_arca_configs()
    return configs[0].get("punto_venta", 1) if configs else 1
