import os
import re


from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.spa import TIPOS_PROPIOS, archivo_publico
from starlette.middleware.base import BaseHTTPMiddleware
import httpx

from app import database as db
from app import config_manager
from app import arca_wsaa
from app import arca_wspadron
from app.security_headers import SecurityHeadersMiddleware
from app.web.auth import require_auth, get_current_user
from app.web.routers import remitos, presupuestos, facturas, config as config_router, webhooks
from app.web.routers import productos as productos_router
from app.web.routers import ventas as ventas_router
from app.web.routers import logs as logs_router
from app.web.routers import reportes as reportes_router
from app.web.routers import libros_iva as libros_iva_router
from app import db_usuarios
from app.web import auth as web_auth
from libraauth.auth_events import AuthEventRepository
from libraauth.demo_codigos import DemoCodigoRepository
from libraauth.session_auth import build_demo_codigos_router, demo_username
from app.web.api import auth as api_auth_router
from app.web.api import dashboard as api_dashboard_router
from app.web.api import resumen as api_resumen_router
from app.web.api import clientes as api_clientes_router
from app.web.api import productos as api_productos_router
from app.web.api import listas_precio as api_listas_precio_router
from app.web.api import proveedores as api_proveedores_router
from app.web.api import egresos as api_egresos_router
from app.web.api import usuarios as api_usuarios_router
from app.web.api import config as api_config_router
from app.web.api import depositos as api_depositos_router
from app.web.api import stock as api_stock_router
from app.web.api import cuenta_corriente as api_cc_router
from app.web.api import recibos as api_recibos_router
from app.web.api import tesoreria as api_tesoreria_router
from app.web.api import caja as api_caja_router
from app.web.api import cajas as api_cajas_router
from app.web.api import turnos as api_turnos_router
from app.web.api import ventas as api_ventas_router
from app.web.api import facturas as api_facturas_router
from app.web.api import remitos as api_remitos_router
from app.web.api import presupuestos as api_presupuestos_router
from app.web.api import mp_bandeja as api_mp_bandeja_router
from app.web.api import libros_iva as api_libros_iva_router
from app.web.api import reportes as api_reportes_router
from app.web.api import logs as api_logs_router
from app.web.api_auth import (  # noqa: F401
    get_current_user_json, require_admin_json, require_admin_o_servicio_json,
)
from app.web.modules_gate import require_module
from libracore.comprobantes_router import (
    build_comprobantes_bandeja_router,
    build_comprobantes_ingesta_router,
)
from libracore.config_router import build_backup_router
from libracore.respaldo import Instancia

app = FastAPI(title="Contalibra")

# ── Lo que el router de auth de libraauth espera en `app.state` ─────────────
#
# Desde el 2026-08-18 los siete endpoints de `/api` los sirve el motor (ver
# `app/web/api/auth.py`). El router los busca en el state en cada request, asi
# que esto tiene que quedar puesto al importar el modulo, igual que el `app`.
#
# 🔴 `auth_events` es lo que alimenta el **rate limiting** del login del motor,
# que reemplaza al que este producto tenia escrito a mano. Escribe en la MISMA
# tabla `auth_log` que ya usaba `db.registrar_auth_event`, asi que el historial
# de accesos no se parte en dos y los intentos viejos siguen contando.
app.state.users = db_usuarios.user_repository()
app.state.session_auth = web_auth.session_auth
app.state.auth_events = AuthEventRepository(db_usuarios.sessions())
app.state.password_reset = db_usuarios.password_reset_service()

# 🔴 Solo en la demo, y **falla cerrado**: una instancia demo que llegue aca
# sin el repositorio deja de dejar entrar, con `503 demo access codes not
# configured`. En la instancia de un cliente no hay demo que abrir.
if demo_username():
    app.state.demo_codigos = DemoCodigoRepository(db_usuarios.sessions())


_BYPASS_PATHS = {"/suspendido", "/favicon.ico", "/api/auth/verify", "/health"}

class CurrentUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/static"):
            return await call_next(request)
        username = get_current_user(request)
        request.state.current_user = db.get_usuario_by_username(username) if username else None
        try:
            cfg = config_manager.load()
            request.state.empresa_nombre   = cfg.get("empresa_nombre", "")
            request.state.servicio_estado  = cfg.get("servicio_estado", "activo")
            request.state.servicio_mensaje = cfg.get("servicio_mensaje", "")
        except Exception:
            request.state.empresa_nombre   = ""
            request.state.servicio_estado  = "activo"
            request.state.servicio_mensaje = ""
        try:
            mods = db.get_modulos()
            request.state.modulos = {m for m, on in mods.items() if on}
        except Exception:
            request.state.modulos = set()
        try:
            request.state.mp_pending_count = db.get_mp_pending_count()
        except Exception:
            request.state.mp_pending_count = 0

        # Corte de servicio: redirigir todo excepto rutas de bypass y archivos estáticos.
        # Para /api/* se devuelve JSON 503 en vez de un redirect -- un redirect a
        # /suspendido (HTML) rompe cualquier fetch/XHR de la SPA, que espera JSON.
        estado = request.state.servicio_estado
        path   = request.url.path
        if (estado == "suspendido"
                and path not in _BYPASS_PATHS
                and not path.startswith("/static")):
            if path.startswith("/api/"):
                return JSONResponse(
                    {"error": "servicio_suspendido", "mensaje": request.state.servicio_mensaje},
                    status_code=503,
                )
            from fastapi.responses import RedirectResponse as _RR
            return _RR("/suspendido")

        return await call_next(request)


app.add_middleware(CurrentUserMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health", include_in_schema=False)
def health():
    """Sin auth, sin lógica de negocio — para Docker HEALTHCHECK y monitoreo
    externo (uptime-kuma). Ver wiki/analyses/restolibra-auditoria-produccion:
    no había ningún endpoint determinístico para chequear que la instancia
    de un cliente esté viva (hallazgo cruzado a este repo)."""
    return {"status": "ok"}


@app.get("/suspendido")
def servicio_suspendido(request: Request):
    return templates.TemplateResponse(request, "suspendido.html", {
        "mensaje": request.state.servicio_mensaje,
        "empresa": request.state.empresa_nombre,
    })


# Routers HTML/descarga viejos que sobreviven al corte de la Etapa D --
# ver wiki/entities/contalibra.md. Cada uno quedo recortado a solo las
# sub-rutas (PDF/ticket/CSV/backup/autocomplete) que la SPA nueva sigue
# consumiendo; las paginas Jinja2 se removieron.
# `GET`/`POST`/`DELETE /admin/demo-codigos`: por donde el backoffice emite los
# codigos que se le pasan a un interesado. Solo en la demo, por lo mismo que el
# repositorio de arriba.
if demo_username():
    app.include_router(build_demo_codigos_router())
app.include_router(remitos.router)
app.include_router(presupuestos.router)
app.include_router(facturas.router)
app.include_router(config_router.router)
app.include_router(webhooks.router)
app.include_router(productos_router.router)
app.include_router(ventas_router.router)
app.include_router(logs_router.router)
app.include_router(reportes_router.router)
app.include_router(libros_iva_router.router)

# API JSON de la SPA (React) -- migracion documentada en
# wiki/entities/contalibra.md. Conviven con los routers HTML de arriba
# hasta la etapa de corte; todo endpoint nuevo va bajo el prefijo /api/.
# El gating (auth + modulo habilitado por plan) se declara aca, centralizado,
# mismo patron que gestiolibra/app/main.py -- no en cada router. (auth.py y
# dashboard.py son la excepcion: gatean via Depends embebido porque /api/me
# necesita el usuario como valor de retorno; el resto de los modulos de la
# Etapa B no lo necesitan, asi que van centralizados aca.)
_auth_json = Depends(get_current_user_json)
app.include_router(api_auth_router.router)
app.include_router(api_dashboard_router.router)
# `resumen` también gatea adentro, con su propia dependencia: acepta la
# credencial del panel del dueño, que no es usuario de esta instancia y por lo
# tanto no pasaría `_auth_json`.
app.include_router(api_resumen_router.router)
app.include_router(
    api_clientes_router.router,
    dependencies=[_auth_json, Depends(require_module("clientes"))],
)
app.include_router(
    api_productos_router.router,
    dependencies=[_auth_json, Depends(require_module("productos"))],
)
app.include_router(
    api_listas_precio_router.router,
    dependencies=[_auth_json, Depends(require_module("listas_precio"))],
)
app.include_router(
    api_proveedores_router.router,
    dependencies=[_auth_json, Depends(require_module("proveedores"))],
)
app.include_router(
    api_egresos_router.router,
    dependencies=[_auth_json, Depends(require_module("egresos"))],
)
app.include_router(
    # Acepta ADEMAS el token de servicio (libraauth v0.7.0): es lo que le
    # permite al backoffice de la suite (admin.contalibra.com.ar) administrar
    # los usuarios de esta instancia sin ser usuario de ella.
    api_usuarios_router.router,
    dependencies=[Depends(require_admin_o_servicio_json)],
)
app.include_router(
    # Solo el correo saliente, no todo `/api/config` — ver el comentario en
    # web/api/config.py sobre por que es un router aparte.
    api_config_router.smtp_router,
    dependencies=[Depends(require_admin_o_servicio_json)],
)
app.include_router(
    api_config_router.router,
    dependencies=[Depends(require_admin_json)],
)
# Datos / Backup, del motor (LibraCore v1.10.0+). Reemplaza a la implementacion
# propia que vivia en `web/routers/config.py` y `web/api/config.py`.
#
# 🔴 La propia estaba ROTA desde el corte a PostgreSQL, en los dos caminos, y
# las dos formas de fallar escribian la URL de la base -- con la contrasena--
# en el mensaje de error:
#
#   - `GET /config/backup-db` hacia `FileResponse(db.DB_PATH)`. Con PostgreSQL
#     eso es una URL, no un archivo: `RuntimeError: File at path
#     postgresql://usuario:CLAVE@host/base does not exist.`
#   - `POST /api/config/restore-db` exigia que el archivo empezara con
#     `SQLite format 3\x00` -- o sea que rechazaba de plano el `.dump` que el
#     propio producto venia generando-- y despues hacia
#     `shutil.move(tmp, db.DB_PATH)`, que sobre una URL crea un archivo **con
#     la contrasena en el nombre**.
#
# Ademas el backup propio se llevaba solo la base: dejaba afuera los logos y
# los **certificados de ARCA**, que son los que dejan facturar. El del motor
# toma la instancia entera.
#
# `cerrar_conexiones`/`reabrir_conexiones` van en None a proposito: este
# producto no sostiene un pool -- `libracore.db.core.get_connection()` abre y
# cierra una conexion por llamada--, asi que no hay descriptor viejo que
# invalidar. En PostgreSQL, ademas, el restore es del lado del servidor.
app.include_router(
    build_backup_router(
        lambda: Instancia(
            nombre="contalibra",
            bases=([] if db.ES_POSTGRES else [db.DB_PATH]),
            postgres_url=(db.DB_PATH if db.ES_POSTGRES else None),
            directorios=[config_router.LOGO_DIR, config_router.CERTS_DIR],
        ),
        config_router.BACKUPS_DIR,
    ),
    dependencies=[Depends(require_admin_json)],
)
app.include_router(
    api_depositos_router.router,
    dependencies=[_auth_json, Depends(require_module("depositos"))],
)
app.include_router(
    api_stock_router.router,
    dependencies=[_auth_json, Depends(require_module("stock"))],
)
app.include_router(
    api_cc_router.router,
    dependencies=[_auth_json, Depends(require_module("cuenta_corriente"))],
)
app.include_router(
    # Sin `require_module` a proposito: un recibo nace de una factura, de una
    # venta o de un pago de cuenta corriente, asi que gatearlo por uno de esos
    # tres modulos dejaria sin reimpresion a los otros dos.
    api_recibos_router.router,
    dependencies=[_auth_json],
)
app.include_router(
    api_tesoreria_router.router,
    dependencies=[Depends(require_admin_json), Depends(require_module("tesoreria"))],
)
app.include_router(
    api_caja_router.router,
    dependencies=[_auth_json, Depends(require_module("caja"))],
)
app.include_router(
    api_cajas_router.router,
    dependencies=[_auth_json, Depends(require_module("cajas"))],
)
app.include_router(
    api_turnos_router.router,
    dependencies=[_auth_json],
)
app.include_router(
    api_ventas_router.router,
    dependencies=[_auth_json, Depends(require_module("ventas"))],
)
app.include_router(
    api_facturas_router.router,
    dependencies=[_auth_json, Depends(require_module("facturacion"))],
)
app.include_router(
    api_remitos_router.router,
    dependencies=[_auth_json, Depends(require_module("remitos"))],
)
app.include_router(
    api_presupuestos_router.router,
    dependencies=[_auth_json, Depends(require_module("presupuestos"))],
)
app.include_router(
    api_mp_bandeja_router.router,
    dependencies=[_auth_json],
)
app.include_router(
    api_libros_iva_router.router,
    dependencies=[Depends(require_admin_json), Depends(require_module("libros_iva"))],
)
app.include_router(
    api_reportes_router.router,
    dependencies=[_auth_json, Depends(require_module("reportes"))],
)
app.include_router(
    api_logs_router.router,
    dependencies=[Depends(require_admin_json)],
)


def _quien_resolvio(request: Request) -> str:
    """Con qué nombre se firma la resolución de un comprobante pendiente.

    Se lee de la sesión y no del payload a propósito: esto es la trazabilidad
    de quién aprobó facturarle algo a alguien, y un campo del cuerpo lo elige
    el cliente. Devuelve vacío en vez de romper si no hay sesión — el gate del
    router ya se ocupó de que la haya.
    """
    try:
        usuario = get_current_user_json(request)
    except HTTPException:
        return ""
    return usuario.get("nombre") or usuario.get("username") or ""


# La bandeja de lo que otro producto de la familia dejó para facturar acá (hoy
# LibraDesk). Van en DOS routers porque no se protegen igual, y el orden de las
# dependencias no alcanzaría: FastAPI evalúa las del router antes que las de la
# ruta. Ver `libracore/comprobantes_router.py`.
app.include_router(
    # Lo deposita otro sistema, sin humano detrás. Mismo gate que Usuarios, que
    # es el otro endpoint que atiende a la suite y no a una persona.
    build_comprobantes_ingesta_router(),
    dependencies=[Depends(require_admin_o_servicio_json)],
)
app.include_router(
    # La bandeja la trabaja una persona, y decide facturar: sólo admin.
    build_comprobantes_bandeja_router(usuario_actual=_quien_resolvio),
    dependencies=[Depends(require_admin_json)],
)


@app.on_event("startup")
def startup():
    db.init_db()
    db.ensure_admin_user()
    # No-op salvo que la instancia sea una demo (DEMO_MODE + DEMO_USERNAME).
    db.ensure_demo_user()


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/dashboard")


DOCS_AUTH_SECRET = os.environ.get("DOCS_AUTH_SECRET", "")


@app.post("/api/auth/verify", include_in_schema=False)
async def api_auth_verify(request: Request):
    """Verificación stateless de credenciales para la landing (acceso a /docs/).

    Server-to-server únicamente: requiere el secreto compartido DOCS_AUTH_SECRET
    en el header X-Internal-Auth. No crea sesión ni cookie en esta instancia.
    """
    if not DOCS_AUTH_SECRET or request.headers.get("x-internal-auth") != DOCS_AUTH_SECRET:
        return JSONResponse({"valid": False}, status_code=401)

    body = await request.json()
    username = str(body.get("username", ""))
    password = str(body.get("password", ""))

    if request.state.servicio_estado != "activo":
        return JSONResponse({"valid": False})

    user = db.check_usuario_credentials(username, password)
    if not user:
        return JSONResponse({"valid": False})

    return JSONResponse({
        "valid": True,
        "nombre_empresa": request.state.empresa_nombre,
    })


@app.get("/api/arca/estado", include_in_schema=False)
def arca_estado(user: str = Depends(require_auth)):
    configs = db.obtener_todas_arca_configs()
    if not configs:
        return JSONResponse({"configurado": False})
    cfg = configs[0]
    cert_path, clave_path = config_manager.resolve_cert_paths(
        cfg.get("certificado_path", ""), cfg.get("clave_path", "")
    )
    tiene_cert  = bool(cert_path) and os.path.exists(cert_path)
    tiene_clave = bool(clave_path) and os.path.exists(clave_path)
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
    cert_path, key_path = config_manager.resolve_cert_paths(
        cfg.get("certificado_path", ""), cfg.get("clave_path", "")
    )
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


@app.get("/api/email/probar", include_in_schema=False)
async def email_probar(user: str = Depends(require_auth)):
    import smtplib
    cfg = config_manager.load()
    host     = cfg.get("email_smtp_host", "").strip()
    port     = int(cfg.get("email_smtp_port", 587) or 587)
    smtp_user = cfg.get("email_smtp_user", "").strip()
    password = cfg.get("email_smtp_password", "").strip()
    if not host or not smtp_user or not password:
        return JSONResponse({"ok": False, "error": "Completá host, usuario y contraseña antes de probar."}, status_code=400)
    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, password)
        return JSONResponse({"ok": True, "host": host, "port": port, "user": smtp_user})
    except smtplib.SMTPAuthenticationError:
        return JSONResponse({"ok": False, "error": "Autenticación fallida. Verificá el usuario y la contraseña de aplicación."}, status_code=401)
    except smtplib.SMTPConnectError as e:
        return JSONResponse({"ok": False, "error": f"No se pudo conectar al servidor: {e}"}, status_code=502)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)


@app.get("/api/mp/probar", include_in_schema=False)
async def mp_probar(user: str = Depends(require_auth)):
    cfg = config_manager.load()
    token = cfg.get("mp_access_token", "").strip()
    if not token:
        return JSONResponse({"ok": False, "error": "No hay Access Token configurado."}, status_code=400)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.mercadopago.com/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        if r.status_code != 200:
            return JSONResponse({"ok": False, "error": f"MP respondió {r.status_code}: {r.text[:200]}"}, status_code=502)
        data = r.json()
        return JSONResponse({
            "ok":        True,
            "user_id":   data.get("id"),
            "nickname":  data.get("nickname"),
            "email":     data.get("email"),
            "site_id":   data.get("site_id"),
            "pais":      data.get("country_id"),
        })
    except httpx.RequestError as e:
        return JSONResponse({"ok": False, "error": f"Sin conexión con MercadoPago: {e}"}, status_code=502)


@app.get("/api/arca/certificado-info", include_in_schema=False)
def arca_cert_info(user: str = Depends(require_auth)):
    configs = db.obtener_todas_arca_configs()
    if not configs:
        return JSONResponse({"error": "Sin configuracion"}, status_code=404)
    cert_path, _ = config_manager.resolve_cert_paths(
        configs[0].get("certificado_path", ""), configs[0].get("clave_path", "")
    )
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

    cert_path, clave_path = config_manager.resolve_cert_paths(
        arca["certificado_path"], arca["clave_path"]
    )
    try:
        ta = await arca_wsaa.autenticar(
            cert_path, clave_path, arca["ambiente"],
            servicio="ws_sr_padron_a13",
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
                    "El certificado no tiene acceso al servicio de Padrón (ws_sr_padron_a13). "
                    "Ingresá a ARCA → Administración de Relaciones → delegá el servicio "
                    "'Consulta a Padrón Alcance 13' para tu CUIT y volvé a intentarlo."
                )
            }, status_code=403)
        return JSONResponse({"error": msg}, status_code=502)
    except Exception as e:
        return JSONResponse({"error": f"Error al consultar ARCA: {e}"}, status_code=500)


# Serving de la SPA (React) -- mismo patron que gestiolibra/app/asgi.py.
# Busca primero /opt/frontend-dist (donde el Dockerfile hornea el stage de
# node, fuera del arbol bind-monteado por docker-compose.yml de dev) y si
# no existe cae al build local del repo (`frontend/dist`), para poder
# levantar la API sola sin haber buildeado nunca el frontend. Registrado al
# final del modulo a proposito: todos los routers de arriba (HTML y /api/)
# ya fueron declarados, asi que el catch-all solo atrapa lo que ningun otro
# endpoint respondio.
_DOCKER_FRONTEND_DIST = "/opt/frontend-dist"
# Tres niveles arriba: app/web/app.py -> app/web -> app -> raiz del repo.
# Eran dos cuando este archivo vivia en web/; al empaquetar (2026-07-31) se
# sumo un nivel. Solo aplica al dev local sin Docker: en el contenedor gana
# _DOCKER_FRONTEND_DIST.
_LOCAL_FRONTEND_DIST = os.path.join(
    os.path.dirname(__file__), "..", "..", "frontend", "dist"
)
FRONTEND_DIST = _DOCKER_FRONTEND_DIST if os.path.isdir(_DOCKER_FRONTEND_DIST) else _LOCAL_FRONTEND_DIST

if os.path.isdir(FRONTEND_DIST):
    from fastapi.responses import FileResponse

    app.mount(
        "/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="frontend-assets"
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        archivo = archivo_publico(FRONTEND_DIST, full_path)
        if archivo is not None:
            return FileResponse(archivo, media_type=TIPOS_PROPIOS.get(archivo.suffix))
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
