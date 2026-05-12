import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import httpx

import database as db
import config_manager
import arca_wsaa
import arca_wspadron
from web.auth import (
    require_auth, check_credentials, get_current_user,
    create_session_cookie, clear_session_cookie,
    SECRET_KEY,
)
from web.routers import clientes, remitos, presupuestos, facturas, config as config_router, caja, webhooks, dashboard
from web.routers import usuarios as usuarios_router
from web.routers import modulos as modulos_router
from web.routers import productos as productos_router
from web.routers import ventas as ventas_router
from web.routers import stock as stock_router
from web.routers import turnos as turnos_router

app = FastAPI(title="Contalibra")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


class CurrentUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        username = get_current_user(request)
        request.state.current_user = db.get_usuario_by_username(username) if username else None
        try:
            request.state.empresa_nombre = config_manager.load().get("empresa_nombre", "")
        except Exception:
            request.state.empresa_nombre = ""
        try:
            mods = db.get_modulos()
            request.state.modulos = {m for m, on in mods.items() if on}
        except Exception:
            request.state.modulos = set()
        return await call_next(request)


app.add_middleware(CurrentUserMiddleware)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(dashboard.router)
app.include_router(clientes.router)
app.include_router(remitos.router)
app.include_router(presupuestos.router)
app.include_router(facturas.router)
app.include_router(config_router.router)
app.include_router(caja.router)
app.include_router(webhooks.router)
app.include_router(usuarios_router.router)
app.include_router(modulos_router.router)
app.include_router(productos_router.router)
app.include_router(ventas_router.router)
app.include_router(stock_router.router)
app.include_router(turnos_router.router)


@app.on_event("startup")
def startup():
    db.init_db()
    db.ensure_admin_user()
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "remitos_pdf"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "presupuestos_pdf"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "facturas_pdf"), exist_ok=True)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/dashboard")


@app.get("/login", include_in_schema=False)
def login_get(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login", include_in_schema=False)
async def login_post(request: Request):
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    if check_credentials(username, password):
        response = RedirectResponse("/dashboard", status_code=303)
        create_session_cookie(response, username)
        return response
    return templates.TemplateResponse(
        request, "login.html", {"error": "Usuario o contraseña incorrectos"}, status_code=401
    )


@app.get("/logout", include_in_schema=False)
def logout():
    response = RedirectResponse("/login", status_code=303)
    clear_session_cookie(response)
    return response


@app.get("/api/arca/estado", include_in_schema=False)
def arca_estado(user: str = Depends(require_auth)):
    configs = db.obtener_todas_arca_configs()
    if not configs:
        return JSONResponse({"configurado": False})
    cfg = configs[0]
    tiene_cert  = bool(cfg.get("certificado_path")) and os.path.exists(cfg.get("certificado_path", ""))
    tiene_clave = bool(cfg.get("clave_path")) and os.path.exists(cfg.get("clave_path", ""))
    return JSONResponse({
        "configurado": tiene_cert and tiene_clave,
        "ambiente": cfg.get("ambiente", ""),
        "cuit": cfg.get("cuit", ""),
        "tiene_certificado": tiene_cert,
        "tiene_clave": tiene_clave,
    })


@app.get("/api/arca/probar", include_in_schema=False)
async def arca_probar(user: str = Depends(require_auth)):
    configs = db.obtener_todas_arca_configs()
    if not configs:
        return JSONResponse({"ok": False, "error": "ARCA no está configurado."}, status_code=400)

    cfg        = configs[0]
    cert_path  = cfg.get("certificado_path", "")
    key_path   = cfg.get("clave_path", "")
    ambiente   = cfg.get("ambiente", "homologacion")

    # Validar archivos localmente primero
    errores = arca_wsaa.validar_archivos(cert_path, key_path)
    if errores:
        return JSONResponse({"ok": False, "error": " | ".join(errores)}, status_code=400)

    # Info del certificado
    info = arca_wsaa.info_certificado(cert_path)

    # Autenticar contra WSAA
    try:
        ta = await arca_wsaa.autenticar(cert_path, key_path, ambiente)
        return JSONResponse({
            "ok": True,
            "ambiente": ambiente,
            "expiracion": ta["expiracion"],
            "cert_vencimiento": info.get("vencimiento"),
            "cert_dias_restantes": info.get("dias_restantes"),
            "cert_subject": info.get("subject"),
        })
    except RuntimeError as e:
        return JSONResponse({"ok": False, "error": str(e), "cert": info}, status_code=502)


@app.get("/api/arca/certificado-info", include_in_schema=False)
def arca_cert_info(user: str = Depends(require_auth)):
    configs = db.obtener_todas_arca_configs()
    if not configs:
        return JSONResponse({"error": "Sin configuracion"}, status_code=404)
    cert_path = configs[0].get("certificado_path", "")
    return JSONResponse(arca_wsaa.info_certificado(cert_path))


@app.get("/api/consultar-cuit/{cuit}", include_in_schema=False)
async def consultar_cuit(cuit: str, user: str = Depends(require_auth)):
    cuit_limpio = re.sub(r"[^0-9]", "", cuit)
    if len(cuit_limpio) != 11:
        return JSONResponse({"error": "CUIT inválido. Debe tener 11 dígitos."}, status_code=400)

    arca_cfg = db.obtener_todas_arca_configs()
    arca     = arca_cfg[0] if arca_cfg else None

    if not arca or not arca.get("certificado_path") or not arca.get("clave_path"):
        return JSONResponse(
            {"error": "Configurá los certificados ARCA en Configuración para habilitar la consulta de CUIT."},
            status_code=503,
        )

    try:
        ta = await arca_wsaa.autenticar(
            arca["certificado_path"], arca["clave_path"], arca["ambiente"],
            servicio="ws_sr_padron_a4",
        )
        datos = await arca_wspadron.consultar_persona(
            arca["cuit"], cuit_limpio, ta["token"], ta["sign"], arca["ambiente"]
        )
        return JSONResponse(datos)

    except RuntimeError as e:
        msg = str(e)
        if "no encontrado" in msg.lower() or "inexistente" in msg.lower():
            return JSONResponse({"error": msg}, status_code=404)
        # Error de autorización del servicio en WSAA
        if "coe" in msg.lower() or "no autorizado" in msg.lower() or "constraints" in msg.lower() or "sin acceso" in msg.lower():
            return JSONResponse({
                "error": (
                    "El certificado no tiene acceso al servicio de Padrón (ws_sr_padron_a4). "
                    "Ingresá a ARCA → Administración de Relaciones → delegá el servicio "
                    "'Consulta a Padrón Alcance 4' para tu CUIT y volvé a intentarlo."
                )
            }, status_code=403)
        return JSONResponse({"error": msg}, status_code=502)
    except Exception as e:
        return JSONResponse({"error": f"Error al consultar ARCA: {e}"}, status_code=500)
