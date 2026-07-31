import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import datetime
import shutil
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import Annotated

import database as db
from web.auth import require_auth, require_role

router = APIRouter(dependencies=[Depends(require_role("admin"))])

Auth = Annotated[str, Depends(require_auth)]

LOGO_DIR    = os.path.join(os.path.dirname(db.DB_PATH), "logos")
CERTS_DIR   = os.path.join(os.path.dirname(db.DB_PATH), "arca_certs")
BACKUPS_DIR = os.path.join(os.path.dirname(db.DB_PATH), "backups")

# Las paginas y formularios Jinja2 de este router (empresa/mp/email/arca/
# servicio/ticket/restore-db/categorias-producto/categorias-egreso) se
# removieron en el corte de la migracion a React -- ver
# wiki/entities/contalibra.md, Etapa D. Solo quedan la descarga del logo
# y los backups de la DB, y los helpers de backup que reusa
# web/api/config.py (importados de aca tal cual, no duplicados).


@router.get("/config/empresa/logo", include_in_schema=False)
def config_logo(user: Auth):
    import config_manager
    cfg = config_manager.load()
    path = config_manager.resolve_logo_path(cfg)
    if not path or not os.path.exists(path):
        raise HTTPException(404)
    ext = os.path.splitext(path)[1].lower()
    media = "image/png" if ext == ".png" else "image/jpeg"
    return FileResponse(path, media_type=media)


def _listar_backups() -> list[dict]:
    """Devuelve los backups automáticos disponibles, ordenados del más reciente al más antiguo."""
    if not os.path.exists(BACKUPS_DIR):
        return []
    result = []
    for f in sorted(os.listdir(BACKUPS_DIR), reverse=True):
        if not f.endswith(".db"):
            continue
        path = os.path.join(BACKUPS_DIR, f)
        stat = os.stat(path)
        result.append({
            "filename": f,
            "size_mb":  round(stat.st_size / 1_048_576, 2),
            "mtime":    datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return result


def _hacer_backup_automatico(motivo: str = "auto") -> str:
    """Hace checkpoint WAL y guarda copia de la DB actual. Retorna la ruta del backup."""
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    # Eliminar backups automáticos que superen los 10 más recientes
    backups = sorted(
        [f for f in os.listdir(BACKUPS_DIR) if f.endswith(".db")],
        reverse=True,
    )
    for old in backups[9:]:
        try:
            os.unlink(os.path.join(BACKUPS_DIR, old))
        except OSError:
            pass
    # Checkpoint WAL antes de copiar
    try:
        with db.get_connection() as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
    except Exception:
        pass
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUPS_DIR, f"backup_{motivo}_{ts}.db")
    shutil.copy2(db.DB_PATH, dest)
    return dest


@router.get("/config/backup-db")
def config_backup_db(user: Auth):
    hoy      = datetime.date.today().strftime("%Y%m%d")
    filename = f"contalibra_backup_{hoy}.db"
    # Checkpoint WAL antes de servir el archivo
    try:
        with db.get_connection() as conn:
            conn.execute("PRAGMA wal_checkpoint(FULL)")
    except Exception:
        pass
    return FileResponse(db.DB_PATH, media_type="application/octet-stream",
                        filename=filename)


@router.get("/config/backup-db/{filename}")
def config_download_autobackup(filename: str, user: Auth):
    """Descarga un backup automático específico."""
    if ".." in filename or "/" in filename:
        raise HTTPException(400)
    path = os.path.join(BACKUPS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path, media_type="application/octet-stream", filename=filename)
