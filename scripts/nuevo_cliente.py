#!/usr/bin/env python3
"""
Onboarding de nuevo cliente Contalibra.
Uso: python3 scripts/nuevo_cliente.py

Wrapper de configuración sobre libracore.provisioning.nuevo_cliente (lógica
compartida con Restolibra, parametrización de este script — ver
wiki/entities/libracore.md). Solo fija las constantes propias de Contalibra;
la lógica real vive en LibraCore.
"""
import os
from pathlib import Path

from libracore.provisioning import configure
from libracore.provisioning.nuevo_cliente import (
    ClienteError,
    ask,
    build_image,
    crear_cliente,
    image_exists,
    main,
    network_exists,
    next_port,
    slugify,
    used_ports,
)

REPO_ROOT = Path(__file__).parent.parent.resolve()

configure(
    postgres=True,
    # ⚠️ **Tiene que decir lo mismo que `scripts/panel_admin.py`.** Hasta el
    # 2026-08-24 este archivo no pasaba `backup_zip` y el otro sí. Como pisan un
    # `_cfg` GLOBAL y `libracore.admin.services` importa los dos módulos en el
    # mismo proceso, una diferencia acá hace que el resultado dependa del orden
    # de los imports. `tests/test_provisioning.py` lo compara entero con
    # `asdict`.
    #
    # **No estaba mordiendo**: todo camino que hoy lee `cfg.backup_zip` entra por
    # `panel_admin.py`, que ya lo tenía en `True`. Se ve en el servidor — las
    # instancias vienen armando su ZIP diario en `data/backups/`. Era una mina,
    # no un incendio.
    #
    # `True` es el valor correcto y no un empate arbitrario: este producto sirve
    # su pantalla de Backups con el `build_backup_router` de `libracore.respaldo`,
    # así que el ZIP del cron es exactamente el que el cliente puede listar,
    # bajar y restaurar solo. Sin el flag, el `tar.gz` empaqueta `data/` mientras
    # el dump de PostgreSQL queda **afuera**.
    backup_zip=True,
    product_name="CONTALIBRA",
    image_name="contalibra:latest",
    container_prefix="contalibra",
    db_filename="contalibra.db",
    # 🔑 **DOS cadenas, y el orden no es decorativo.** Tiene que decir lo MISMO
    # que `panel_admin.py` y que el `command:` de dev del compose; hay un test
    # que ata las tres puntas.
    #
    # 1. `libracore-migrar` — el schema de LibraCore, que hasta el 2026-08-25
    #    **no lo corría nadie**: sus migraciones no viajaban en el wheel.
    #    Resuelve la base por `CONTALIBRA_DATABASE_URL`: acá el schema del core
    #    vive en la MISMA base que el dominio, así que la resolución cae a la
    #    del dominio a propósito — ver `libracore.migrar.url_de_core`.
    #
    # 2. `alembic` — la cadena **propia**, agregada el 2026-08-25. Gobierna las
    #    3 tablas que son de este producto (`venta_links`,
    #    `integraciones_config`, `ventas_origen_externo`); las otras 58 son de
    #    los motores. Va SEGUNDA porque `venta_links` tiene FK contra
    #    `facturas`, `remitos` y `turnos_caja`, que son de LibraCore.
    #
    # 🔴 Acá esto importa **más** que en el deploy: en un alta las migraciones
    # corren ANTES del primer arranque, así que la baseline es lo primero que
    # toca la base después del motor — no hay `init_db()` que le haya dejado las
    # tablas de LibraCommerce puestas. Por eso la baseline llama a
    # `init_commerce_schema()` ella misma; ver su docstring.
    migraciones=(
        ("libracore-migrar", "upgrade", "--prefijo", "contalibra"),
        ("alembic", "upgrade", "head"),
    ),
    repo_root=REPO_ROOT,
    base_port=8071,
    docs_auth_secret=os.environ.get("DOCS_AUTH_SECRET", ""),
)

# Re-exportados por compatibilidad con `libracore.admin.services` (import
# nuevo_cliente as nc) y con cualquier uso directo de este módulo.
CLIENTES_DIR = REPO_ROOT / "clientes"

if __name__ == "__main__":
    main()
