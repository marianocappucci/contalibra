import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import httpx

import database as db
from web.auth import (
    require_auth, check_credentials,
    create_session_cookie, clear_session_cookie,
    SECRET_KEY,
)
from web.routers import clientes, remitos, presupuestos, config as config_router

app = FastAPI(title="Contalibra")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(clientes.router)
app.include_router(remitos.router)
app.include_router(presupuestos.router)
app.include_router(config_router.router)


@app.on_event("startup")
def startup():
    db.init_db()
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "remitos_pdf"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "presupuestos_pdf"), exist_ok=True)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/remitos")


@app.get("/login", include_in_schema=False)
def login_get(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login", include_in_schema=False)
async def login_post(request: Request):
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    if check_credentials(username, password):
        response = RedirectResponse("/remitos", status_code=303)
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


@app.get("/api/consultar-cuit/{cuit}", include_in_schema=False)
async def consultar_cuit(cuit: str, user: str = Depends(require_auth)):
    cuit_limpio = re.sub(r"[^0-9]", "", cuit)
    if len(cuit_limpio) != 11:
        return JSONResponse({"error": "CUIT inválido. Debe tener 11 dígitos."}, status_code=400)

    url = f"https://soa.afip.gob.ar/sr-padron/v2/persona/{cuit_limpio}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code == 404:
            return JSONResponse({"error": "CUIT no encontrado en ARCA."}, status_code=404)
        if resp.status_code != 200:
            return JSONResponse({"error": f"ARCA respondió con error {resp.status_code}."}, status_code=502)

        data = resp.json().get("data", {})
        if not data:
            return JSONResponse({"error": "No se encontraron datos para ese CUIT."}, status_code=404)

        # Armar nombre
        if data.get("tipoPersona") == "JURIDICA":
            nombre = data.get("razonSocial") or data.get("nombre", "")
        else:
            apellido = data.get("apellido", "")
            nombre_p = data.get("nombre", "")
            nombre = f"{apellido}, {nombre_p}".strip(", ")

        # Domicilio fiscal
        dom = data.get("domicilioFiscal", {})
        calle = dom.get("calle", "")
        numero = dom.get("numero", "")
        localidad = dom.get("localidad", "")
        provincia = dom.get("descripcionProvincia", "")
        domicilio_parts = [p for p in [f"{calle} {numero}".strip(), localidad, provincia] if p]
        domicilio = ", ".join(domicilio_parts)

        # Condición IVA
        impuestos = data.get("impuestos", [])
        iva_condition = ""
        if 30 in impuestos:
            iva_condition = "Responsable Inscripto"
        elif 32 in impuestos:
            iva_condition = "Monotributista"
        elif 48 in impuestos:
            iva_condition = "IVA Exento"

        return JSONResponse({
            "nombre": nombre,
            "domicilio": domicilio,
            "iva_condition": iva_condition,
            "estado": data.get("estadoClave", ""),
        })

    except httpx.TimeoutException:
        return JSONResponse({"error": "Tiempo de espera agotado al consultar ARCA."}, status_code=504)
    except Exception as e:
        return JSONResponse({"error": f"Error al consultar ARCA: {str(e)}"}, status_code=500)
