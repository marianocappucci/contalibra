import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import Annotated

from app import database as db
from app.web.auth import require_auth, require_role

router = APIRouter(dependencies=[Depends(require_role("admin"))])

Auth = Annotated[str, Depends(require_auth)]

# 🔴 De `DATA_DIR` y NO de `os.path.dirname(db.DB_PATH)`, que es como estaba.
# Con la base en PostgreSQL `db.DB_PATH` es una URL, y `dirname()` de
# `postgresql://usuario:clave@host:5432/base` devuelve
# `postgresql://usuario:clave@host:5432`: las tres carpetas quedaban colgando de
# una ruta inventada **con la contrasena en el nombre**. Y no son carpetas
# cualquiera -- ahi viven el logo de la empresa y los **certificados de ARCA**,
# que son los que dejan facturar.
#
# La carpeta de datos siempre fue esta; la ruta de la base era una forma
# indirecta de llegar que funcionaba solo mientras la base fuera un archivo.
_DATA_DIR = os.environ.get("DATA_DIR") or os.path.dirname(os.path.abspath(db.__file__))

LOGO_DIR    = os.path.join(_DATA_DIR, "logos")
CERTS_DIR   = os.path.join(_DATA_DIR, "arca_certs")
BACKUPS_DIR = os.path.join(_DATA_DIR, "backups")

# Las paginas y formularios Jinja2 de este router (empresa/mp/email/arca/
# servicio/ticket/restore-db/categorias-producto/categorias-egreso) se
# removieron en el corte de la migracion a React -- ver
# wiki/entities/contalibra.md, Etapa D. Solo quedan la descarga del logo
# y las tres rutas de datos (`LOGO_DIR`, `CERTS_DIR`, `BACKUPS_DIR`), que
# `web/api/config.py` y el router de backup del motor importan de aca.


@router.get("/config/empresa/logo", include_in_schema=False)
def config_logo(user: Auth):
    from app import config_manager
    cfg = config_manager.load()
    path = config_manager.resolve_logo_path(cfg)
    if not path or not os.path.exists(path):
        raise HTTPException(404)
    ext = os.path.splitext(path)[1].lower()
    media = "image/png" if ext == ".png" else "image/jpeg"
    return FileResponse(path, media_type=media)


# 🔴 Acá vivían `_listar_backups()`, `_hacer_backup_automatico()` y las rutas
# `/config/backup-db[/{filename}]`. Se removieron el 2026-08-12: la pantalla de
# Datos / Backup pasa a salir de `libracore.respaldo`, igual que en los otros
# cuatro productos. El router del motor se monta en `web/app.py`, y `BACKUPS_DIR`
# de acá arriba es el directorio que recibe.
#
# **No fue una normalización de prolijidad: lo propio estaba roto.** Desde el
# corte a PostgreSQL del 2026-08-09/10, los dos caminos fallaban escribiendo la
# URL de la base —con la contraseña— en el mensaje de error:
#
#   - `GET /config/backup-db` servía `FileResponse(db.DB_PATH)`, y con
#     PostgreSQL eso es una URL, no un archivo.
#   - `POST /api/config/restore-db` exigía `SQLite format 3\x00`, o sea que
#     rechazaba de plano el `.dump` que el propio producto generaba, y después
#     hacía `shutil.move(tmp, db.DB_PATH)` sobre esa misma URL.
#
# Y aun andando, el backup propio se llevaba **sólo la base**: los logos y los
# certificados de ARCA —los que dejan facturar— quedaban afuera. El del motor
# toma la instancia entera, en un ZIP.
#
# Los archivos `.db`/`.dump` que ya estén en `BACKUPS_DIR` dejan de aparecer en
# la pantalla, porque el motor lista `.zip`. Medido antes de decidirlo: las dos
# instancias con clientes reales tenían **cero** archivos ahí, así que no se le
# saca nada a nadie. Los de las demos quedan en disco y se los lleva el reset.
