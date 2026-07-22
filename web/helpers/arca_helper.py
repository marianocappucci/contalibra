"""Shim de compatibilidad — la implementación real vive en libracore (paquete
interno, ver requirements.txt y wiki/entities/libracore.md). No editar el
comportamiento acá; los cambios van en el repo libracore."""
from libracore.arca_facturacion import (  # noqa: F401
    get_next_numero_with_arca,
    solicitar_cae,
)
