"""API JSON de Cuenta Corriente para la SPA (ver
wiki/entities/contalibra.md, migracion a React). Reusa
`db_cuenta_corriente.py` (via `database.py`) tal cual -- ver
web/api/clientes.py para el patron general de esta etapa."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import database as db
from app import db_recibos
from app.web.api_auth import get_current_user_json, require_admin_json

logger = logging.getLogger("contalibra.cuenta_corriente")

router = APIRouter(prefix="/api/cuenta-corriente", tags=["cuenta_corriente"])


class PagoPayload(BaseModel):
    monto: float
    fecha: str
    concepto: str = "Pago a cuenta"
    referencia: str = ""
    medio_pago: str = "efectivo"
    caja_id: int | None = None


@router.get("")
def listar():
    clientes = db.get_clientes_con_saldo_cc()
    total_deuda = sum(c["saldo"] for c in clientes if c["saldo"] > 0)
    return {"clientes": clientes, "total_deuda": total_deuda}


@router.get("/cajas")
def listar_cajas():
    """Solo lectura, para el selector de caja del pago -- CRUD de cajas
    (modulo Caja/Cajas) es Etapa C."""
    return db.get_all_cajas()


@router.get("/{cliente_id}")
def detalle(cliente_id: int):
    cliente = db.get_client(cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    return {
        "cliente": cliente,
        "movimientos": db.get_cc_movimientos(cliente_id),
        "saldo": db.get_cc_saldo(cliente_id),
    }


@router.post("/{cliente_id}/pagar")
def pagar(cliente_id: int, payload: PagoPayload, user: dict = Depends(get_current_user_json)):
    cliente = db.get_client(cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")

    pago_id = db.create_cc_pago(
        cliente_id=cliente_id, monto=payload.monto, fecha=payload.fecha,
        concepto=payload.concepto, referencia=payload.referencia,
        medio_pago=payload.medio_pago, caja_id=payload.caja_id, usuario_id=user["id"],
    )

    if payload.caja_id:
        db.create_caja_movimiento(
            fecha=payload.fecha, tipo="ingreso", concepto=f"Pago CC - {cliente['name']}",
            monto=payload.monto, referencia=payload.referencia,
            caja_id=payload.caja_id, medio_pago=payload.medio_pago, usuario_id=user["id"],
        )

    # El recibo sale con el cobro, no cuando alguien se acuerda: quien acaba de
    # cobrar tiene al cliente enfrente esperando el papel. Se devuelve el id
    # para que la pantalla lo abra sola.
    #
    # Si fallara la emision, el cobro **ya esta registrado** y no se revierte:
    # perder el comprobante es molesto, perder el pago es un problema de plata.
    # El boton por movimiento lo vuelve a intentar, y es idempotente.
    recibo_id = None
    try:
        recibo_id = db.emitir_recibo_cobranza(pago_id, usuario_id=user["id"])["id"]
    except Exception:
        logger.exception("No se pudo emitir el recibo del cc_pago %s", pago_id)

    return {
        "movimientos": db.get_cc_movimientos(cliente_id),
        "saldo": db.get_cc_saldo(cliente_id),
        "recibo_id": recibo_id,
    }


@router.delete("/pagos/{pago_id}", dependencies=[Depends(require_admin_json)])
def eliminar_pago(pago_id: int, user: dict = Depends(get_current_user_json)):
    # Anular el recibo ANTES de borrar el pago: si el pago se va primero, su
    # recibo queda apuntando a una fila que no existe y sigue figurando como
    # vigente en el listado — un comprobante de un cobro que el sistema ya no
    # reconoce. Se anula en vez de borrarse porque el papel pudo haber salido
    # impreso, y el numero queda consumido igual.
    for recibo in db_recibos.get_recibos_de_origen(db_recibos.ORIGEN_CC_PAGO, pago_id):
        db.anular_recibo(recibo["id"], motivo="Se elimino el pago que lo origino",
                         usuario_id=user["id"])
    db.delete_cc_pago(pago_id)
    return {"ok": True}
