#!/usr/bin/env python3
"""
Panel de administración Contalibra.
Gestiona todos los contenedores de clientes desde un menú interactivo.
Uso: python3 scripts/panel_admin.py [comando] [slug]
     python3 scripts/panel_admin.py           → menú interactivo
     python3 scripts/panel_admin.py listar
     python3 scripts/panel_admin.py backup micomercio

Wrapper de configuración sobre libracore.provisioning.panel_admin (lógica
compartida con Restolibra, parametrización de este script — ver
wiki/entities/libracore.md). Solo fija las constantes propias de Contalibra;
la lógica real vive en LibraCore.
"""
import os
from pathlib import Path

from libracore.provisioning import configure, client_from_config, forward_host_from_config, le_email_from_config, npm_available
from libracore.provisioning.panel_admin import (
    cli, cmd_activar, cmd_backup, cmd_backup_all, cmd_eliminar, cmd_estado_servicio,
    cmd_info, cmd_list_backups, cmd_listar, cmd_logs, cmd_npm_crear, cmd_npm_eliminar,
    cmd_npm_listar, cmd_pausar, cmd_restart, cmd_restore_db, cmd_start, cmd_stop,
    cmd_suspender, cmd_actualizar, compose, container_status, find_client, interactive,
    load_clients, pick_client, _set_servicio_estado,
)

REPO_ROOT = Path(__file__).parent.parent.resolve()

configure(
    # El backup del cron arma el MISMO ZIP que la pantalla de Backups, en
    # `data/backups/`, en vez de un `tar.gz` aparte que la pantalla no lista
    # y el cliente no puede restaurar. Requiere libracore >= v1.29.0.
    #
    # Este producto puede prenderlo porque su pantalla sale de
    # `libracore.respaldo` (`build_backup_router` en app/main.py). Contalibra
    # y Restolibra tienen implementacion propia y todavia no.
    backup_zip=True,
    # 🔴 **Esto lo encontró `tests/test_provisioning.py` apenas se agregó.** Este
    # archivo no pasaba `docs_auth_secret` y `nuevo_cliente.py` sí, y no es
    # cosmético: el único que lo lee es el alta, que lo estampa como
    # `DOCS_AUTH_SECRET=` en el `.env` de la instancia nueva. Como los dos pisan
    # el mismo `_cfg` global y `libracore.admin.services` importa los dos
    # módulos, un alta hecha desde el backoffice —donde este archivo puede ser
    # el último import— habría creado la instancia con el secreto **vacío**.
    #
    # No se veía comparando las dos configuraciones en un entorno sin
    # `DOCS_AUTH_SECRET` seteada: ahí las dos ramas dan `""` y el desvío
    # desaparece. Aparece en el CI, que sí la setea.
    docs_auth_secret=os.environ.get("DOCS_AUTH_SECRET", ""),
    postgres=True,
    product_name="CONTALIBRA",
    image_name="contalibra:latest",
    container_prefix="contalibra",
    db_filename="contalibra.db",
    # 🔑 **DOS cadenas, y el orden no es decorativo.**
    #
    # 1. `libracore-migrar` — el schema de LibraCore, que hasta el 2026-08-25
    #    **no lo corría nadie**: sus migraciones no viajaban en el wheel. Medido
    #    ese día: de las tres instancias de este producto, la de dev estaba en
    #    `0002` y las otras en `0001_baseline` o **sin `alembic_version`
    #    ninguna** — producción atrás de dev, y sin las cuatro columnas que la
    #    revisión `0002` le agrega a `clients`.
    #
    #    Resuelve la base por `CONTALIBRA_DATABASE_URL`: acá el schema del core
    #    vive en la MISMA base que el dominio, así que la resolución cae a la
    #    del dominio a propósito — ver `libracore.migrar.url_de_core`.
    #
    # 2. `alembic` — la cadena **propia**, agregada el 2026-08-25. Gobierna las
    #    3 tablas que son de este producto (`venta_links`,
    #    `integraciones_config`, `ventas_origen_externo`); las otras 58 son de
    #    los motores. Va SEGUNDA porque `venta_links` tiene FK contra
    #    `facturas`, `remitos` y `turnos_caja`, que son de LibraCore: al revés,
    #    la baseline muere con `relation "facturas" does not exist` en un alta
    #    nueva, donde las migraciones corren antes del primer arranque.
    #
    #    Usa `alembic_version_contalibra`, no `alembic_version` — esa última es
    #    la del motor y corre contra esta misma base. Ver `migrations/env.py`.
    #
    # Son dos comandos y no un `sh -c "a && b"` para que el `[ERROR]` del deploy
    # diga **cuál de las dos** falló, que es el dato que uno necesita a las tres
    # de la mañana.
    migraciones=(
        ("libracore-migrar", "upgrade", "--prefijo", "contalibra"),
        ("alembic", "upgrade", "head"),
    ),
    repo_root=REPO_ROOT,
    base_port=8071,
)

# Re-exportados por compatibilidad con `libracore.admin.services` (import
# panel_admin as pa) y con cualquier uso directo de este módulo.
CLIENTES_DIR = REPO_ROOT / "clientes"
_NPM_AVAILABLE = npm_available()

if __name__ == "__main__":
    cli()
