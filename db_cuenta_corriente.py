"""Cuenta corriente por cliente de Contalibra.

El dominio es de LibraCore (dinero: `cc_pagos`, `caja_movimientos`,
`facturas`). Lo único propio de Contalibra es **de qué tabla salen las
ventas**: desde P7 viven en `sales` (ver `db_ventas.py`), no en `ventas`.

Hasta el 2026-07-28 eso obligaba a copiar el módulo entero acá para cambiar
un `JOIN` — y Restolibra tenía su propia copia idéntica, con lo cual el
mismo cálculo de dinero existía tres veces. Ahora LibraCore recibe el origen
como parámetro (`OrigenVentas`) y este módulo sólo declara cuál usa.

El criterio de cálculo (débitos por venta + débitos por factura + débitos
directos − abonos) no cambió en ningún momento.
"""
from functools import partial

from libracore.db import cuenta_corriente as _cc
from libracore.db.cuenta_corriente import VENTAS_LIBRACOMMERCE
# Estas dos no dependen del origen de las ventas: se usan tal cual.
from libracore.db.cuenta_corriente import (  # noqa: F401
    create_cc_pago,
    delete_cc_pago,
)

get_cc_saldo = partial(_cc.get_cc_saldo, origen=VENTAS_LIBRACOMMERCE)
get_cc_movimientos = partial(_cc.get_cc_movimientos, origen=VENTAS_LIBRACOMMERCE)
get_cc_movimientos_periodo = partial(
    _cc.get_cc_movimientos_periodo, origen=VENTAS_LIBRACOMMERCE
)
get_clientes_con_saldo_cc = partial(
    _cc.get_clientes_con_saldo_cc, origen=VENTAS_LIBRACOMMERCE
)
