import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from typing import Annotated

import config_manager
from web.auth import require_auth

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))

Auth = Annotated[str, Depends(require_auth)]

LOGO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logos")


@router.get("/config")
def config_get(request: Request, user: Auth):
    return templates.TemplateResponse(request, "config.html", {
        "cfg": config_manager.load(), "active": "config", "saved": False,
    })


@router.post("/config")
async def config_post(request: Request, user: Auth):
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
        "cfg": cfg, "active": "config", "saved": True,
    })
