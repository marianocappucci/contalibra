"""Version JSON de /dashboard (web/routers/dashboard.py) para la SPA --
misma logica (libracore.db.dashboard.get_dashboard_data vía database.py),
sin renderizar template. El modulo "dashboard" no esta en la tabla
`modulos` (ver database.py::init_db, _MODULOS_DEFAULT) -- no se gatea por
plan, igual que la version HTML.
"""
import datetime

from fastapi import APIRouter, Depends

from app import database as db
from app.web.api_auth import get_current_user_json

router = APIRouter(prefix="/api", tags=["dashboard"])

_TIPO_LETRA = {1: "A", 6: "B", 11: "C"}


@router.get("/dashboard")
def dashboard(user: dict = Depends(get_current_user_json)):
    hoy = datetime.date.today()
    mes_desde = hoy.replace(day=1).isoformat()
    mes_hasta = hoy.isoformat()

    data = db.get_dashboard_data(mes_desde, mes_hasta)

    for f in data["facturas_sin_cobrar"]:
        f["letra"] = _TIPO_LETRA.get(f["tipo"], "")
        pv = str(f["punto_venta"]).zfill(4)
        num = str(f["numero"]).zfill(8)
        f["label_numero"] = f"{pv}-{num}"

    return {
        **data,
        "mes_desde": mes_desde,
        "mes_hasta": mes_hasta,
    }
