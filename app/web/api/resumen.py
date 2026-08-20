"""`GET /api/resumen` — los numeros de esta sucursal, para el panel del dueño.

El endpoint **no se implementa aca**: lo arma la factory de [[libracore]]
(`build_resumen_router`), y este modulo se limita a cablear las tres piezas que
sabe el producto.

Asi fue desde el 2026-08-20, cuando la Fase 0 —escrita entera en este repo para
poder probarla contra una instancia real antes de mover nada— se mudo a los
motores. Sus tests (`tests/test_resumen.py`) **no se tocaron en la mudanza**:
son la red que dice si el endrouter del motor contesta lo mismo que la copia
local que reemplazo.

Ver wiki/analyses/panel-del-dueno-multisucursal.md.
"""
from libraauth.session_auth import json_api_require_panel_o_admin
from libracommerce.db.repository import SqliteCommerceRepository
from libracore.resumen_router import build_resumen_router

from app import config_manager
from app import database as db
from app.db_core import get_connection


def _identidad() -> dict:
    """Quien es esta sucursal, para que el panel la sepa nombrar y agrupar.

    El CUIT es lo que permite el consolidado **por razon social**, que es el
    unico que cierra contra los libros: sumar entre CUITs da un numero de
    gestion, no uno declarable.
    """
    cfg = config_manager.load()
    arca = db.obtener_todas_arca_configs()
    return {
        "nombre": cfg.get("empresa_nombre", ""),
        "cuit": cfg.get("empresa_cuit", ""),
        "punto_venta": arca[0].get("punto_venta") if arca else None,
    }


def _comercio(desde: str, hasta: str) -> dict:
    """Ventas y stock, del motor comercial.

    Contalibra monta [[libracommerce]], asi que **manda** este bloque. Un
    producto que no lo monte simplemente no lo pasa, y el panel no lo va a ver
    en cero: no lo va a ver.
    """
    with get_connection() as conn:
        return SqliteCommerceRepository(conn).resumen_comercio(desde, hasta)


router = build_resumen_router(
    identidad=_identidad,
    # El guard viene de libraauth y no de libracore: los dos son motores peers y
    # libracore no depende de aquel. El producto, que depende de los dos, es el
    # que los une.
    guard=json_api_require_panel_o_admin,
    bloques={"comercio": _comercio},
)
