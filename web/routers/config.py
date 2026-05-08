import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

import config_manager
import database as db
from web.auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

Auth = Annotated[str, Depends(require_auth)]

LOGO_DIR  = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logos")
CERTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "arca_certs")


def _arca_cfg():
    configs = db.obtener_todas_arca_configs()
    return configs[0] if configs else {}


@router.get("/config")
def config_get(request: Request, user: Auth, tab: str = "empresa"):
    return templates.TemplateResponse(request, "config.html", {
        "cfg": config_manager.load(),
        "arca": _arca_cfg(),
        "active": "config",
        "tab": tab,
        "saved": None,
    })


@router.post("/config/empresa")
async def config_empresa_post(request: Request, user: Auth):
    form = await request.form()
    existing = config_manager.load()
    cfg = {
        "empresa_nombre":    str(form.get("empresa_nombre", "")).strip(),
        "empresa_direccion": str(form.get("empresa_direccion", "")).strip(),
        "empresa_cuit":      str(form.get("empresa_cuit", "")).strip(),
        "empresa_telefono":  str(form.get("empresa_telefono", "")).strip(),
        "empresa_email":     str(form.get("empresa_email", "")).strip(),
        "empresa_iibb":      str(form.get("empresa_iibb", "")).strip(),
        "logo_path":         existing.get("logo_path", ""),
    }
    logo_file = form.get("logo")
    if logo_file and hasattr(logo_file, "filename") and logo_file.filename:
        ext = os.path.splitext(logo_file.filename)[1].lower()
        if ext in (".png", ".jpg", ".jpeg"):
            os.makedirs(LOGO_DIR, exist_ok=True)
            logo_path = os.path.join(LOGO_DIR, f"logo{ext}")
            content = await logo_file.read()
            with open(logo_path, "wb") as f:
                f.write(content)
            cfg["logo_path"] = logo_path
    config_manager.save(cfg)
    return templates.TemplateResponse(request, "config.html", {
        "cfg": cfg, "arca": _arca_cfg(),
        "active": "config", "tab": "empresa", "saved": "empresa",
    })


# Mantener compatibilidad con el POST anterior
@router.post("/config")
async def config_post_compat(request: Request, user: Auth):
    return await config_empresa_post(request, user)


@router.post("/config/arca")
async def config_arca_post(request: Request, user: Auth):
    form = await request.form()
    empresa     = str(form.get("empresa", "")).strip() or "default"
    cuit        = str(form.get("cuit", "")).strip()
    punto_venta = int(form.get("punto_venta", "1") or "1")
    ambiente    = str(form.get("ambiente", "homologacion")).strip()
    alias       = str(form.get("alias", "")).strip()

    os.makedirs(CERTS_DIR, exist_ok=True)

    existing = db.obtener_arca_config(empresa) or {}
    clave_path = existing.get("clave_path", "")
    cert_path  = existing.get("certificado_path", "")

    # Guardar clave privada si se subió
    clave_file = form.get("clave_privada")
    if clave_file and hasattr(clave_file, "filename") and clave_file.filename:
        clave_path = os.path.join(CERTS_DIR, "clave_privada.key")
        with open(clave_path, "wb") as f:
            f.write(await clave_file.read())

    # Guardar certificado si se subió
    cert_file = form.get("certificado")
    if cert_file and hasattr(cert_file, "filename") and cert_file.filename:
        cert_path = os.path.join(CERTS_DIR, "certificado.crt")
        with open(cert_path, "wb") as f:
            f.write(await cert_file.read())

    if existing:
        db.actualizar_arca_config(
            empresa, cuit=cuit, punto_venta=punto_venta,
            clave_path=clave_path, certificado_path=cert_path,
            ambiente=ambiente, alias=alias,
        )
    else:
        db.crear_arca_config(
            empresa=empresa, cuit=cuit, punto_venta=punto_venta,
            clave_path=clave_path, certificado_path=cert_path,
            ambiente=ambiente, alias=alias,
        )

    return templates.TemplateResponse(request, "config.html", {
        "cfg": config_manager.load(), "arca": _arca_cfg(),
        "active": "config", "tab": "arca", "saved": "arca",
    })
