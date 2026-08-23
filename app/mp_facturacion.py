"""Shim de compatibilidad — la implementación real vive en libracore (paquete
interno, ver pyproject.toml y wiki/entities/libracore.md). No editar el
comportamiento acá; los cambios van en el repo libracore.

Este módulo nació en este repo y subió al motor el 2026-08-23, al normalizar la
facturación electrónica de la suite. La copia de Restolibra **no** era
equivalente: resolvía el pagador sin mirar los alias de facturación, que es el
mecanismo que acá emitió dos comprobantes al CUIT equivocado (RIPEHO
2026-07-10, VISCO 2026-08-03).
"""
from libracore.mp_facturacion import (  # noqa: F401
    CONDICION_POR_PAYMENT_TYPE,
    IVA_CODES,
    TIPO_LABEL,
    TIPO_POR_CONDICION,
    generar_factura_mp,
    resolver_cliente,
)
