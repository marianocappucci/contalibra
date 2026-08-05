"""Recibos de Contalibra.

Todo el dominio es de LibraCore (`libracore.db.recibos` para los datos,
`libracore.recibos` para la emisión). Lo único propio de Contalibra es **de
qué tabla salen las ventas**: desde P7 viven en `sales` de LibraCommerce (ver
`db_ventas.py`), no en `ventas`.

Por eso `emitir_recibo_venta` se liga acá al `get_venta` del producto. Si se
dejara el default del motor —`libracore.db.ventas.get_venta`, que lee la tabla
`ventas`— el recibo de una venta saldría vacío o directamente no saldría, y no
por un error visible: la tabla existe en esta base (la crea el schema core) y
simplemente está vacía. Mismo motivo y mismo patrón que
`db_cuenta_corriente.py`, que le pasa `VENTAS_LIBRACOMMERCE` al cálculo del
saldo.

Los otros dos orígenes no necesitan nada: la factura y el pago a cuenta viven
en tablas de LibraCore en esta misma base.
"""
from functools import partial

from libracore import recibos as _recibos
# Re-exportadas tal cual: la capa de datos no depende del producto.
from libracore.db.recibos import (  # noqa: F401
    ORIGEN_CC_PAGO,
    ORIGEN_FACTURA,
    ORIGEN_VENTA,
    anular_recibo,
    contar_recibos,
    get_recibo,
    get_recibos,
    get_recibos_de_origen,
)
from libracore.recibos import SinCobros  # noqa: F401

from app import db_ventas

emitir_recibo_cobranza = _recibos.emitir_recibo_cobranza
emitir_recibo_factura = _recibos.emitir_recibo_factura
emitir_recibo_venta = partial(_recibos.emitir_recibo_venta,
                              get_venta=db_ventas.get_venta)
