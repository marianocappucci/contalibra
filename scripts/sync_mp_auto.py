#!/usr/bin/env python3
"""Sincronización nocturna de MercadoPago con auto-facturación.

    docker exec contalibra python3 /app/scripts/sync_mp_auto.py [--dias N]

🔑 **Es el camino que emite la mayoría de las facturas de MercadoPago**, y el
que corre sin nadie mirando. Desde el 2026-08-23 el trabajo lo hace
`libracore.mp_sync`, que comparte la ingesta con el botón *Sincronizar* de la
bandeja: tenerlas separadas es lo que dejó a este script afuera del cambio que
introdujo los alias de facturación, y le costó dos comprobantes emitidos al CUIT
equivocado (RIPEHO 2026-07-10, VISCO 2026-08-03).

Acá queda sólo lo que es de este producto: qué cobros omitir y la regla de
*Hosting Mensual*, las mismas dos que usa el webhook.
"""
import asyncio
import logging
import os
import sys

# Este script corre POR RUTA desde cron, asi que sys.path[0] es /app/scripts y
# no /app: sin esto no encuentra el paquete `app`. En el resto del repo el
# insert se saco al empaquetar (2026-07-31), porque ahi sobraba; aca es lo unico
# que sostiene el import y hay un test que lo vigila
# (tests/test_layout_paquete.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libracore.mp_sync import sincronizar_y_facturar  # noqa: E402

from app.web.routers.webhooks import _es_hosting_mensual  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main(argv=None) -> dict:
    import argparse

    parser = argparse.ArgumentParser(description="Sync automatico de MercadoPago")
    parser.add_argument("--dias", type=int, default=2,
                        help="Dias hacia atras a sincronizar (default: 2)")
    args = parser.parse_args(argv)
    return asyncio.run(sincronizar_y_facturar(
        dias=args.dias,
        # Los cobros por QR de una venta presencial no van a la bandeja.
        referencias_a_omitir=("venta-",),
        # 🔑 La MISMA funcion que usa el webhook, importada y no reescrita: es
        # exactamente la divergencia que este script ya tuvo una vez.
        debe_auto_facturar=_es_hosting_mensual,
    ))


if __name__ == "__main__":
    main()
