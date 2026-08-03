"""Shim de compatibilidad — la implementación real vive en libracore (paquete
interno, ver pyproject.toml y wiki/entities/libracore.md). No editar el
comportamiento acá; los cambios van en el repo libracore."""
from libracore.config_manager import (  # noqa: F401
    CONFIG_PATH, LOGO_DIR, CERTS_DIR, DEFAULTS,
    load, save, resolve_logo_path, resolve_cert_paths,
)
