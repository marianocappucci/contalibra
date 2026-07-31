"""API JSON de Logs de actividad para la SPA (ver
wiki/entities/contalibra.md, migracion a React). Reusa `db_logs.py` (via
`database.py`) tal cual -- ver web/api/clientes.py para el patron general
de esta etapa. Admin-only (gateado en web/app.py con require_admin_json).
El export CSV (`GET /admin/logs/export`) sigue en
`web/routers/logs.py` sin tocar, la SPA lo linkea directo.

Modulo detectado como faltante recien al preparar el corte de la Etapa D
(quedo afuera del inventario original de las Etapas B/C) -- se completa
aca antes de remover las rutas HTML viejas para no perder la
funcionalidad."""
import database as db
from fastapi import APIRouter

router = APIRouter(prefix="/api/logs", tags=["logs"])

PAGE_SIZE = 100

TIPO_META = {
    "venta": {"label": "Venta", "color": "#0d6efd"},
    "caja": {"label": "Caja", "color": "#198754"},
    "stock": {"label": "Stock", "color": "#6f42c1"},
    "factura": {"label": "Factura", "color": "#0dcaf0"},
    "turno": {"label": "Turno", "color": "#fd7e14"},
    "remito": {"label": "Remito", "color": "#6c757d"},
    "presupuesto": {"label": "Presupuesto", "color": "#20c997"},
}


@router.get("")
def listar(tipo: str = "", usuario_id: int = 0, turno_id: int = 0, desde: str = "", hasta: str = "", page: int = 1):
    tipos_sel = [t.strip() for t in tipo.split(",") if t.strip()] if tipo else []
    offset = (page - 1) * PAGE_SIZE

    actividad = db.get_actividad_log(
        tipos=tipos_sel or None, usuario_id=usuario_id or None, turno_id=turno_id or None,
        desde=desde, hasta=hasta, limit=PAGE_SIZE, offset=offset,
    )
    total = db.get_actividad_count(
        tipos=tipos_sel or None, usuario_id=usuario_id or None, turno_id=turno_id or None,
        desde=desde, hasta=hasta,
    )

    return {
        "actividad": actividad,
        "tipo_meta": TIPO_META,
        "total": total,
        "total_pages": max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
        "page": page,
        "usuarios": db.get_all_usuarios(),
        "auth_log": db.get_auth_log(limit=100),
    }
