"""Shim de compatibilidad — la implementación real vive en libracore (paquete
interno, ver pyproject.toml y wiki/entities/libracore.md). No editar el
comportamiento acá; los cambios van en el repo libracore."""
from libracore.config_manager import (  # noqa: F401
    CERTS_DIR,
    CONFIG_PATH,
    DEFAULTS,
    LOGO_DIR,
    load,
    resolve_cert_paths,
    resolve_logo_path,
    save,
)
