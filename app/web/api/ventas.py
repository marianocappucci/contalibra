"""El punto de venta de este producto: las factories de los dos motores con las
opciones que son de acá (P9-M3, 2026-09-06).

Hasta M3 este archivo era la API completa —idéntica a la del otro producto—.
Ahora es sólo el armado:

- `router`: `GET`/`POST /api/ventas`, el detalle y la anulación, de
  `libracommerce.web.ventas_router` (el motor comercial).
- `cobro`: `/facturar`, `/mp-qr` y `/mp-status` bajo el mismo prefijo, de
  `libracore.ventas_cobro_router` (dinero y comprobantes son de LibraCore),
  sobre el `PuertoDeVentas` de `venta_facturacion`.
- `cobro_legado`: lo mismo bajo `/ventas`, donde vivía hasta M3 (router legado):
  la SPA anterior y la suite pegan ahí. Sin gate por módulo, como el que reemplaza.

`app.py` los monta con el mismo gate (`require_module("ventas")`).
"""
from libracommerce.erp import SIN_GANCHOS as GANCHOS
from libracommerce.web.ventas_router import OpcionesVentas, build_ventas_router
from libracore.ventas_cobro_router import ClienteMercadoPago, build_cobro_de_ventas_router

from app import database as db
from app import mp_api, venta_facturacion
from app.web.api_auth import get_current_user_json, require_role_json


def _stock_habilitado() -> bool:
    return bool(db.get_modulos().get("stock"))


# El cliente de MercadoPago se resuelve en cada llamada y a través del shim
# `app.mp_api`, que es donde la suite lo intercepta (`monkeypatch.setattr(mp_api, ...)`).
_MERCADOPAGO = ClienteMercadoPago(
    crear_orden_qr=lambda **kw: mp_api.crear_orden_qr(**kw),
    buscar_pago_por_referencia=lambda ref, token: mp_api.buscar_pago_por_referencia(ref, token),
)


router = build_ventas_router(
    conexion=db.get_connection,
    usuario_actual=get_current_user_json,
    solo_admin=require_role_json("admin"),
    opciones=OpcionesVentas(stock_habilitado=_stock_habilitado, hooks=GANCHOS),
)

cobro = build_cobro_de_ventas_router(
    ventas=venta_facturacion.PUERTO, usuario_actual=get_current_user_json,
    mercadopago=_MERCADOPAGO,
)

cobro_legado = build_cobro_de_ventas_router(
    ventas=venta_facturacion.PUERTO, usuario_actual=get_current_user_json,
    prefix="/ventas", mercadopago=_MERCADOPAGO,
)
