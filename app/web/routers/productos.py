import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from typing import Annotated, Literal
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

import database as db
from web.auth import require_auth

router = APIRouter()
Auth = Annotated[str, Depends(require_auth)]

# Las paginas Jinja2 de este router (list/nuevo/editar) se removieron en
# el corte de la migracion a React -- ver wiki/entities/contalibra.md,
# Etapa D. Solo queda el autocompletado, que la SPA nueva (Ventas.tsx)
# sigue usando tal cual para el POS.


@router.get("/productos/buscar")
def productos_buscar(q: str = "", lista_id: int = 0, tipo: Literal["", "producto", "servicio"] = "", user: Auth = None):
    """Endpoint JSON para autocompletar en ventas/facturas.

    `tipo` ('producto'|'servicio') es opcional -- Facturas lo usa para
    restringir las sugerencias al Concepto ARCA elegido (Productos vs.
    Servicios vs. ambos), ya que antes dejaba agregar cualquier producto
    a una factura marcada como solo uno de los dos tipos."""
    resultados = db.get_all_productos(solo_activos=True, q=q, tipo=tipo)[:20]
    precios_lista: dict = db.get_precios_lista_dict(lista_id) if lista_id else {}
    return JSONResponse([{
        "id":          p["id"],
        "codigo":      p["codigo"] or "",
        "nombre":      p["nombre"],
        "precio_venta": precios_lista.get(p["id"], p["precio_venta"]),
        "precio_base": p["precio_venta"],
        "unidad":      p["unidad"],
    } for p in resultados])
