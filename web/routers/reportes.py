import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import csv
import io
import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

import database as db
from web.auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

Auth = Annotated[str, Depends(require_auth)]

_HOY  = lambda: datetime.date.today().isoformat()
_MES  = lambda: datetime.date.today().replace(day=1).isoformat()


def _fechas_default(desde: str, hasta: str):
    if not desde:
        desde = _MES()
    if not hasta:
        hasta = _HOY()
    return desde, hasta


@router.get("/reportes")
def reportes_get(
    request: Request, user: Auth,
    desde: str = "", hasta: str = "",
    agrupacion: str = "dia",
):
    desde, hasta = _fechas_default(desde, hasta)
    resumen    = db.get_reporte_resumen(desde, hasta)
    ventas_ts  = db.get_reporte_ventas(desde, hasta, agrupacion)
    medios     = db.get_reporte_medios_pago(desde, hasta)
    productos  = db.get_reporte_productos_top(desde, hasta)
    caja       = db.get_reporte_caja(desde, hasta)
    stock_bajo = db.get_reporte_stock_bajo()
    return templates.TemplateResponse(request, "reportes/index.html", {
        "active":     "reportes",
        "desde":      desde,
        "hasta":      hasta,
        "agrupacion": agrupacion,
        "resumen":    resumen,
        "ventas_ts":  ventas_ts,
        "medios":     medios,
        "productos":  productos,
        "caja":       caja,
        "stock_bajo": stock_bajo,
    })


@router.get("/reportes/export/ventas")
def export_ventas(request: Request, user: Auth, desde: str = "", hasta: str = "", agrupacion: str = "dia"):
    desde, hasta = _fechas_default(desde, hasta)
    rows = db.get_reporte_ventas(desde, hasta, agrupacion)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["periodo", "cantidad", "total"])
    w.writeheader(); w.writerows(rows)
    buf.seek(0)
    fn = f"ventas_{desde}_{hasta}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@router.get("/reportes/export/medios")
def export_medios(request: Request, user: Auth, desde: str = "", hasta: str = ""):
    desde, hasta = _fechas_default(desde, hasta)
    rows = db.get_reporte_medios_pago(desde, hasta)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["medio", "operaciones", "total"])
    w.writeheader(); w.writerows(rows)
    buf.seek(0)
    fn = f"medios_pago_{desde}_{hasta}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})


@router.get("/reportes/export/productos")
def export_productos(request: Request, user: Auth, desde: str = "", hasta: str = ""):
    desde, hasta = _fechas_default(desde, hasta)
    rows = db.get_reporte_productos_top(desde, hasta, limit=500)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["nombre", "cantidad", "total"])
    w.writeheader(); w.writerows(rows)
    buf.seek(0)
    fn = f"productos_top_{desde}_{hasta}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})
