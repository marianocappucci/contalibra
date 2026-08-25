
import csv
import io
import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import Annotated

from libracore import medios_pago

from app import database as db
from app.web.auth import require_auth

router = APIRouter()

Auth = Annotated[str, Depends(require_auth)]

_HOY  = lambda: datetime.date.today().isoformat()
_MES  = lambda: datetime.date.today().replace(day=1).isoformat()


def _fechas_default(desde: str, hasta: str):
    if not desde:
        desde = _MES()
    if not hasta:
        hasta = _HOY()
    return desde, hasta

# La pagina Jinja2 principal (`/reportes`) y la de caja por medio
# (`/reportes/caja-medios`) se removieron en el corte de la migracion a
# React -- ver wiki/entities/contalibra.md, Etapa D. Quedan los exports
# CSV, que la SPA nueva (Reportes.tsx) linkea directo. `_pivot_caja_medios`/
# `_totales_por_medio`/`MEDIO_LABEL` se mantienen porque
# web/api/reportes.py los reusa tal cual (importados de aca, no
# duplicados).


@router.get("/reportes/export/ventas")
def export_ventas(user: Auth, desde: str = "", hasta: str = "", agrupacion: str = "dia"):
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
def export_medios(user: Auth, desde: str = "", hasta: str = ""):
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
def export_productos(user: Auth, desde: str = "", hasta: str = ""):
    desde, hasta = _fechas_default(desde, hasta)
    rows = db.get_reporte_productos_top(desde, hasta, limit=500)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["nombre", "cantidad", "total"])
    w.writeheader(); w.writerows(rows)
    buf.seek(0)
    fn = f"productos_top_{desde}_{hasta}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})


# 🔴 Las etiquetas salen del motor. Este mapa era una de las 28 copias del
# vocabulario, y una de las que ya divergía: decía "Billetera" donde el resto de
# la casa dice "Otras billeteras", y "Cuenta Corriente" con dos mayúsculas.
#
# `sin_especificar` NO es un medio: es lo que el SQL del reporte pone cuando la
# columna viene nula, así que se resuelve acá y no en el vocabulario de la
# familia — meterlo allá lo haría elegible en un selector.
_SIN_MEDIO = {"sin_especificar": "Sin especificar", "": "Sin especificar"}

#: El mapa completo que consume la SPA (`GET /api/reportes/caja-medios` lo
#: devuelve como `medio_label`). Lleva **los históricos también**: un reporte
#: mira meses para atrás, y ahí hay filas con `tarjeta`, `mercado_pago` y
#: `cuenta corriente` con espacio. Sin ellas, esas filas salían con el slug
#: crudo justo en la pantalla donde se cuadra la caja.
MEDIO_LABEL = {**medios_pago.CONOCIDOS, **_SIN_MEDIO}


def _medio_label(medio: str) -> str:
    return MEDIO_LABEL.get(medio, medio)


def _pivot_caja_medios(rows: list) -> list:
    """
    Convierte las filas planas en una lista de cajas con medios pivoteados.
    Cada caja: {nombre, medios: {medio: {ingresos, ingresos_ops, egresos, egresos_ops}},
                total_ingresos, total_egresos, saldo}
    """
    cajas: dict = {}
    for r in rows:
        cid = r["caja_id"]
        if cid not in cajas:
            cajas[cid] = {"nombre": r["caja_nombre"], "medios": {}}
        medio = r["medio"]
        if medio not in cajas[cid]["medios"]:
            cajas[cid]["medios"][medio] = {"ingresos": 0.0, "ingresos_ops": 0,
                                           "egresos": 0.0, "egresos_ops": 0}
        if r["tipo"] == "ingreso":
            cajas[cid]["medios"][medio]["ingresos"]     += float(r["total"])
            cajas[cid]["medios"][medio]["ingresos_ops"] += int(r["operaciones"])
        else:
            cajas[cid]["medios"][medio]["egresos"]      += float(r["total"])
            cajas[cid]["medios"][medio]["egresos_ops"]  += int(r["operaciones"])

    result = []
    for cid, data in cajas.items():
        ti = sum(m["ingresos"] for m in data["medios"].values())
        te = sum(m["egresos"]  for m in data["medios"].values())
        result.append({
            "id":             cid,
            "nombre":         data["nombre"],
            "medios":         data["medios"],
            "total_ingresos": ti,
            "total_egresos":  te,
            "saldo":          ti - te,
        })
    return result


def _totales_por_medio(cajas_pivot: list) -> dict:
    """Suma de ingresos/egresos por medio a través de todas las cajas."""
    totales: dict = {}
    for caja in cajas_pivot:
        for medio, vals in caja["medios"].items():
            if medio not in totales:
                totales[medio] = {"ingresos": 0.0, "ingresos_ops": 0,
                                  "egresos": 0.0, "egresos_ops": 0}
            totales[medio]["ingresos"]     += vals["ingresos"]
            totales[medio]["ingresos_ops"] += vals["ingresos_ops"]
            totales[medio]["egresos"]      += vals["egresos"]
            totales[medio]["egresos_ops"]  += vals["egresos_ops"]
    return dict(sorted(totales.items()))


@router.get("/reportes/caja-medios/export")
def export_caja_medios(user: Auth, desde: str = "", hasta: str = "", caja_id: int = 0):
    desde, hasta = _fechas_default(desde, hasta)
    rows = db.get_reporte_caja_medios(desde, hasta, caja_id)
    buf  = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Caja", "Medio de cobro", "Tipo", "Operaciones", "Total"])
    for r in rows:
        w.writerow([r["caja_nombre"], _medio_label(r["medio"]), r["tipo"],
                    r["operaciones"], r["total"]])
    buf.seek(0)
    fn = f"caja_medios_{desde}_{hasta}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{fn}"'})
