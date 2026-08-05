"""API JSON de Recibos para la SPA.

El recibo es un documento de LibraCore desde `v1.9.0` (antes era un PDF
armado al vuelo, sin numero ni registro — ver wiki/entities/libracore.md).
Este router es el cableado del producto: emite, lista, sirve el PDF y anula.

**No lleva `require_module`.** Un recibo nace de una factura, de una venta o
de un pago de cuenta corriente, asi que gatearlo por uno de esos modulos
dejaria sin reimpresion a los otros dos. El gate real esta en el boton que
lo emite, que si vive dentro de su modulo.

Emitir es idempotente en los tres origenes (la factura acumula, los otros
dos son 1:1), asi que estos POST se pueden repetir sin duplicar nada — ver
el docstring de `libracore.recibos`.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app import database as db
from app.web.api_auth import get_current_user_json, require_admin_json
from libracore.pdf_generator import generate_pdf_recibo_doc
from libracore.recibos import SinCobros

router = APIRouter(prefix="/api/recibos", tags=["recibos"])

_PAGE_SIZE = 50


class AnularPayload(BaseModel):
    motivo: str = ""


def _numero_visible(recibo: dict) -> str:
    return f"{str(recibo['punto_venta']).zfill(4)}-{str(recibo['numero']).zfill(8)}"


def _resumen(recibo: dict) -> dict:
    """Lo que necesita el listado. Sin el snapshot de pagos, que solo importa
    en el PDF y hace pesada la grilla."""
    return {
        "id":             recibo["id"],
        "numero_visible": _numero_visible(recibo),
        "fecha":          recibo["fecha"],
        "cliente_id":     recibo["cliente_id"],
        "cliente_razon":  recibo["cliente_razon"],
        "cliente_cuit":   recibo["cliente_cuit"],
        "concepto":       recibo["concepto"],
        "origen_tipo":    recibo["origen_tipo"],
        "origen_id":      recibo["origen_id"],
        "total":          recibo["total"],
        "anulado":        recibo["anulado"],
        "anulado_motivo": recibo["anulado_motivo"],
    }


@router.get("")
def listar(desde: str = "", hasta: str = "", q: str = "", cliente_id: int | None = None,
           incluir_anulados: bool = True, page: int = 1,
           user: dict = Depends(get_current_user_json)):
    page = max(1, page)
    filtros = dict(desde=desde, hasta=hasta, q=q, cliente_id=cliente_id,
                   incluir_anulados=incluir_anulados)
    recibos = db.get_recibos(**filtros, limit=_PAGE_SIZE, offset=(page - 1) * _PAGE_SIZE)
    total = db.contar_recibos(**filtros)
    return {
        "recibos":   [_resumen(r) for r in recibos],
        "total":     total,
        "page":      page,
        "page_size": _PAGE_SIZE,
    }


@router.get("/{recibo_id}")
def detalle(recibo_id: int, user: dict = Depends(get_current_user_json)):
    recibo = db.get_recibo(recibo_id)
    if not recibo:
        raise HTTPException(404, "Recibo no encontrado")
    return {**_resumen(recibo), "pagos": recibo["pagos"],
            "observaciones": recibo["observaciones"]}


@router.get("/{recibo_id}/pdf")
def pdf(recibo_id: int, user: dict = Depends(get_current_user_json)):
    recibo = db.get_recibo(recibo_id)
    if not recibo:
        raise HTTPException(404, "Recibo no encontrado")
    return Response(
        content=generate_pdf_recibo_doc(recibo),
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'inline; filename="recibo_{_numero_visible(recibo)}.pdf"'},
    )


@router.post("/factura/{factura_id}")
def emitir_de_factura(factura_id: int, user: dict = Depends(get_current_user_json)):
    try:
        recibo = db.emitir_recibo_factura(factura_id, usuario_id=user["id"])
    except SinCobros as exc:
        raise HTTPException(409, str(exc))
    return _resumen(recibo)


@router.post("/venta/{venta_id}")
def emitir_de_venta(venta_id: int, user: dict = Depends(get_current_user_json)):
    try:
        recibo = db.emitir_recibo_venta(venta_id, usuario_id=user["id"])
    except SinCobros as exc:
        raise HTTPException(409, str(exc))
    return _resumen(recibo)


@router.post("/cobranza/{cc_pago_id}")
def emitir_de_cobranza(cc_pago_id: int, user: dict = Depends(get_current_user_json)):
    try:
        recibo = db.emitir_recibo_cobranza(cc_pago_id, usuario_id=user["id"])
    except SinCobros as exc:
        raise HTTPException(409, str(exc))
    return _resumen(recibo)


@router.post("/{recibo_id}/anular", dependencies=[Depends(require_admin_json)])
def anular(recibo_id: int, payload: AnularPayload,
           user: dict = Depends(get_current_user_json)):
    """Anula el recibo. **No toca la caja ni la cuenta corriente**: el recibo
    es el comprobante del cobro, no el cobro. Revertir la plata es la baja del
    pago, que es otra operacion y otro boton."""
    recibo = db.get_recibo(recibo_id)
    if not recibo:
        raise HTTPException(404, "Recibo no encontrado")
    if not db.anular_recibo(recibo_id, motivo=payload.motivo, usuario_id=user["id"]):
        raise HTTPException(409, "El recibo ya estaba anulado.")
    return _resumen(db.get_recibo(recibo_id))
