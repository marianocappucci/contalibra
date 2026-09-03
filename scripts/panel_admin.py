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
import subprocess
import sys
from pathlib import Path

from libracore.provisioning import (
    client_from_config,
    configure,
    forward_host_from_config,
    le_email_from_config,
    npm_available,
)
from libracore.provisioning.panel_admin import (
    _set_servicio_estado,
    cli,
    cmd_activar,
    cmd_actualizar,
    cmd_backup,
    cmd_backup_all,
    cmd_eliminar,
    cmd_estado_servicio,
    cmd_info,
    cmd_list_backups,
    cmd_listar,
    cmd_logs,
    cmd_npm_crear,
    cmd_npm_eliminar,
    cmd_npm_listar,
    cmd_pausar,
    cmd_restart,
    cmd_restore_db,
    cmd_start,
    cmd_stop,
    cmd_suspender,
    compose,
    container_status,
    find_client,
    interactive,
    load_clients,
    pick_client,
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

def _addon(argv: list[str]) -> bool:
    """`panel_admin.py addon <slug> <addon> on|off`.

    Prende o apaga un add-on (módulo suelto de `plans.ADDONS`, ej. `mayorista`)
    en la instancia de un cliente. Un add-on no pertenece a ningún plan, así que
    el `set_plan` del backoffice no lo toca; este comando es el MVP para
    habilitarlo (el botón en el backoffice queda como paso aparte).

    Corre `set_addon` DENTRO del contenedor —donde `libracore.db.core` apunta al
    PostgreSQL de la instancia—, igual que el alta aplica el plan
    (`nuevo_cliente._aplicar_plan_en_contenedor`). El efecto es inmediato:
    `require_module` relee `get_modulos()` en cada request, sin necesidad de
    reiniciar.
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import plans  # el plans.py del producto, que declara ADDONS

    disponibles = ", ".join(sorted(plans.ADDONS)) or "(ninguno)"
    if len(argv) != 3 or argv[2] not in ("on", "off"):
        print("Uso: panel_admin.py addon <slug> <addon> on|off")
        print(f"Add-ons: {disponibles}")
        return False
    slug, addon, estado = argv
    if addon not in plans.ADDONS:
        print(f"Add-on desconocido: {addon!r}. Disponibles: {disponibles}")
        return False
    cliente = find_client(slug)
    if not cliente:
        print(f"Cliente no encontrado: {slug!r}")
        return False

    on = "True" if estado == "on" else "False"
    codigo = (
        "import sys; sys.path.insert(0, '/app'); "
        f"from app.database import set_addon; set_addon({addon!r}, {on})"
    )
    r = subprocess.run(
        ["docker", "exec", cliente["container"], "python3", "-c", codigo],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"[ERROR] no se pudo aplicar el add-on en {slug!r}: {(r.stderr or r.stdout).strip()}")
        return False
    print(f"[OK] add-on {addon!r} {'habilitado' if estado == 'on' else 'deshabilitado'} en {slug!r}")
    return True


if __name__ == "__main__":
    # El add-on es un comando propio de este wrapper (módulo suelto, no un plan):
    # `cli()` de LibraCore no lo conoce. El resto de los comandos van a `cli()`.
    if len(sys.argv) >= 2 and sys.argv[1] == "addon":
        if _addon(sys.argv[2:]) is False:
            sys.exit(1)
    else:
        cli()
