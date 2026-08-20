"""`GET /api/resumen` — los números de esta instancia, para el panel del dueño.

Una sucursal contesta por sí misma; el panel pregunta a las cinco y suma. Ese
reparto es lo que evita que el panel tenga credenciales de cinco bases: le
alcanza con hablarles por HTTP. Ver
`wiki/analyses/panel-del-dueno-multisucursal.md`.

El endpoint **es de sólo lectura y no tiene efectos**. Un panel que además
opere es otro producto.
"""
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from app import config_manager
from app import database as db
from app import db_resumen
from app.web.api_auth import require_panel_o_admin_json

router = APIRouter(prefix="/api", tags=["resumen"])


def _identidad() -> dict:
    """Quién es esta sucursal, para que el panel la sepa nombrar y agrupar.

    El CUIT es lo que permite el consolidado **por razón social**, que es el
    único que cierra contra los libros: sumar entre CUITs da un número de
    gestión, no uno declarable.
    """
    cfg = config_manager.load()
    arca = db.obtener_todas_arca_configs()
    return {
        "nombre": cfg.get("empresa_nombre", ""),
        "cuit": cfg.get("empresa_cuit", ""),
        "punto_venta": arca[0].get("punto_venta") if arca else None,
    }


@router.get("/resumen")
def resumen(
    desde: str = Query(default=""),
    hasta: str = Query(default=""),
    _: dict = Depends(require_panel_o_admin_json),
):
    """Totales del período. Sin `desde`/`hasta`, el mes en curso.

    Las fechas van en ISO (`aaaa-mm-dd`) y no en el formato de pantalla: es una
    API entre máquinas, y el estándar de la familia es que las URLs lleven ISO
    aunque la interfaz muestre dd-mm-aaaa.
    """
    hoy = datetime.date.today()
    desde = desde or hoy.replace(day=1).isoformat()
    hasta = hasta or hoy.isoformat()

    for etiqueta, valor in (("desde", desde), ("hasta", hasta)):
        try:
            datetime.date.fromisoformat(valor)
        except ValueError:
            raise HTTPException(422, f"`{etiqueta}` tiene que ser una fecha ISO (aaaa-mm-dd)")

    if desde > hasta:
        raise HTTPException(422, "`desde` no puede ser posterior a `hasta`")

    return {"instancia": _identidad(), **db_resumen.get_resumen(desde, hasta)}
