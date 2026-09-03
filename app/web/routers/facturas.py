
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from libracore.pdf_generator import generate_pdf_recibo_doc
from libracore.recibos import SinCobros

from app import database as db
from app import pdf_generator as pdf_gen
from app.web.auth import require_auth

router = APIRouter()

Auth = Annotated[str, Depends(require_auth)]


def _usuario_id(username: str):
    """`require_auth` de este router devuelve el **username**, no el usuario
    (la API JSON de la SPA usa `get_current_user_json`, que sí devuelve el
    dict). Para dejar registrado quién emitió el recibo hay que resolverlo."""
    usuario = db.get_usuario_by_username(username)
    return usuario["id"] if usuario else None

# Las paginas y acciones Jinja2 de este router (list/nueva/detail/
# autorizar/enviar-email/eliminar/nota-credito/nota-debito/cobrar/
# borrador-pdf) se removieron en el corte de la migracion a React -- ver
# wiki/entities/contalibra.md, Etapa D. Solo quedan las descargas de
# PDF/ticket/recibo, que la SPA nueva (web/api/facturas.py) linkea
# directo.


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


@router.get("/facturas/{factura_id}/ticket")
def factura_ticket(factura_id: int, user: Auth):
    from app import ticket_generator
    factura = db.get_factura(factura_id)
    if not factura:
        raise HTTPException(404)
    pdf_bytes = ticket_generator.generar_ticket_factura(factura)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="ticket_factura_{factura_id}.pdf"'},
    )


@router.get("/facturas/{factura_id}/recibo")
def factura_recibo(factura_id: int, user: Auth):
    """El recibo de los cobros de una factura, como **documento numerado**.

    Este link lo sigue armando `libra-ui/FacturaDetalle`, asi que no se puede
    mover: lo que cambia es lo que devuelve. Antes generaba un PDF al vuelo que
    cambiaba solo cuando llegaba un cobro posterior; ahora emite (o recupera,
    que es idempotente) el recibo de LibraCore y sirve ese.
    """
    try:
        recibo = db.emitir_recibo_factura(factura_id, usuario_id=_usuario_id(user))
    except SinCobros as exc:
        raise HTTPException(404, detail=str(exc))
    pv  = str(recibo["punto_venta"]).zfill(4)
    num = str(recibo["numero"]).zfill(8)
    return Response(
        content=generate_pdf_recibo_doc(recibo),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_{pv}-{num}.pdf"'},
    )
