"""La bandeja de MercadoPago de Contalibra.

Toda la pantalla vive en `libracore.mp_bandeja_router` desde el 2026-08-23. Acá
queda sólo el armado, con lo único que es de este producto: los cobros con
`external_reference` `venta-…` **no entran a la bandeja**, porque pertenecen a
una venta presencial y su factura sale del circuito de ventas.

El prefijo se mantiene en `/api/mp-bandeja`, que es el que la SPA ya consume.
"""
from libracore.mp_bandeja_router import build_mp_bandeja_router

router = build_mp_bandeja_router(
    prefix="/api/mp-bandeja",
    referencias_a_omitir=("venta-",),
)
