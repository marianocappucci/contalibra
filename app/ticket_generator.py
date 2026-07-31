"""Shim de compatibilidad — la implementación real vive en libracore
(`libracore.ticket_generator`), extraída desde acá el 2026-07-28.

Restolibra tenía una copia byte-a-byte de las 385 líneas de este módulo, así
que el mismo generador de tickets térmicos existía dos veces. No editar el
comportamiento acá; los cambios van en el repo libracore.
"""
from libracore.ticket_generator import (  # noqa: F401
    generar_ticket_factura,
    generar_ticket_venta,
)
