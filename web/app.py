import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

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
