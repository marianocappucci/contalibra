"""Las descargas de una venta: el ticket y el recibo numerado.

Las páginas Jinja2 de este router (list/nueva/detail/anular) se removieron en
el corte de la migración a React. El cobro por QR (`mp-qr`/`mp-status`) vivió
acá hasta P9-M3 (2026-09-06): ahora es `libracore.ventas_cobro_router`,
montado en `/api/ventas` y —por compatibilidad con la SPA y la suite— también
en `/ventas`. Quedan sólo las dos descargas, que la SPA linkea directo.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from libracore.pdf_generator import generate_pdf_recibo_doc
from libracore.recibos import SinCobros

from app import database as db
from app.web.auth import require_auth

router = APIRouter()
Auth = Annotated[str, Depends(require_auth)]


def _usuario_id(username: str):
    """`require_auth` devuelve el username, no el usuario — ver la nota igual
    en `routers/facturas.py`."""
    usuario = db.get_usuario_by_username(username)
    return usuario["id"] if usuario else None


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

    Este link lo arman `Ventas` y `VentaDetalle`, así que no se puede mover.
    """
    try:
        recibo = db.emitir_recibo_venta(vid, usuario_id=_usuario_id(user))
    except SinCobros as exc:
        raise HTTPException(404, detail=str(exc)) from None
    pv = str(recibo["punto_venta"]).zfill(4)
    num = str(recibo["numero"]).zfill(8)
    return Response(
        content=generate_pdf_recibo_doc(recibo),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_{pv}-{num}.pdf"'},
    )
