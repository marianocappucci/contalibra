import os

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from libraauth.auditoria import agregar_middleware_de_usuario, registrador_dbapi
from libraauth.auth_events import AuthEventRepository
from libraauth.demo_codigos import DemoCodigoRepository
from libraauth.migrar import exigir_schema_al_dia
from libraauth.session_auth import build_demo_codigos_router, demo_username
from libraauth.terminos import TerminosRepository, build_terminos_router
from libracommerce.web.catalogo_router import (
    OpcionesDepositos,
    build_depositos_router,
    build_productos_router,
    build_stock_router,
)
from libracommerce.web.listas_router import (
    build_buscar_productos_router,
    build_cliente_lista_router,
    build_listas_precio_router,
    build_quiebres_router,
)
from libracore import auditoria as auditoria_del_motor
from libracore.adicionales_router import build_adicionales_router
from libracore.arca_router import build_arca_router
from libracore.caja_router import OpcionesCajas, build_caja_router, build_cajas_router, build_turnos_router
from libracore.candados import una_vez_al_arrancar
from libracore.clientes_router import build_clientes_router
from libracore.comprobantes_router import (
    build_comprobantes_bandeja_router,
    build_comprobantes_ingesta_router,
)
from libracore.config_router import (
    build_backup_router,
    build_empresa_admin_router,
    build_empresa_router,
)
from libracore.consultar_cuit_router import build_consultar_cuit_router
from libracore.cuenta_corriente_router import build_cuenta_corriente_router
from libracore.dashboard_router import build_dashboard_router
from libracore.db.cuenta_corriente import VENTAS_LIBRACOMMERCE
from libracore.docs_api import cerrar_docs_de_la_api
from libracore.egresos_router import build_egresos_router, build_proveedores_router
from libracore.errores import instalar_registro_de_errores
from libracore.estado_del_sistema import build_estado_del_sistema_router
from libracore.facturas_router import smtp_efectivo
from libracore.libros_iva_router import build_libros_iva_export_router, build_libros_iva_router
from libracore.logs_router import build_logs_export_router, build_logs_router
from libracore.mp_config_router import build_mp_config_router
from libracore.reportes_router import build_reportes_export_router, build_reportes_router
from libracore.resguardo_enlace import build_resguardo_enlace_router
from libracore.respaldo import Instancia
from libracore.smtp_router import build_smtp_probe_router
from libracore.tema_router import build_tema_admin_router, build_tema_router
from libracore.tesoreria_router import build_tesoreria_router
from libraedge.pantalla_del_central import create_nodos_router
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from app import config_manager, db_usuarios, venta_facturacion
from app import database as db
from app.db_core import get_connection as _abrir_conexion
from app.db_reportes import REPORTES
from app.offline import aprovisionamiento as aprovisionamiento_offline
from app.offline import nodos_del_central, sucursales_con_nodo
from app.security_headers import SecurityHeadersMiddleware
from app.spa import montar_spa
from app.sucursal_unica import sucursal_predeterminada
from app.web import auth as web_auth
from app.web.api import auth as api_auth_router
from app.web.api import config as api_config_router
from app.web.api import facturas as api_facturas_router
from app.web.api import integraciones as api_integraciones_router
from app.web.api import mp_bandeja as api_mp_bandeja_router
from app.web.api import presupuestos as api_presupuestos_router
from app.web.api import recibos as api_recibos_router
from app.web.api import remitos as api_remitos_router
from app.web.api import resumen as api_resumen_router
from app.web.api import usuarios as api_usuarios_router
from app.web.api import ventas as api_ventas_router
from app.web.api_auth import (  # noqa: F401
    get_current_user_json,
    require_admin_json,
    require_admin_o_servicio_json,
    require_admin_o_servicio_o_integracion_json,
    require_solo_servicio_json,
)
from app.web.auth import get_current_user, require_admin, require_auth, require_role
from app.web.modules_gate import require_module
from app.web.routers import config as config_router
from app.web.routers import facturas, presupuestos, remitos, sincronizacion_offline, webhooks
from app.web.routers import ventas as ventas_router

app = FastAPI(title="Contalibra")
cerrar_docs_de_la_api(app)

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
# Terminos y Condiciones del Servicio: la prueba de la aceptacion y lo que
# enciende el gate. MISMA fabrica de sesiones que el resto del motor de auth --
# la tabla tiene FK a `usuarios`, que en este producto vive en la base de
# LibraCore.
#
# 🔴 Sin esta linea el gate NO corta y la instancia no falla: se queda sin gate,
# en silencio. Por eso hay un test que lo prueba (`tests/test_terminos_gate.py`).
app.state.terminos = TerminosRepository(db_usuarios.sessions())

# 🔴 Solo en la demo, y **falla cerrado**: una instancia demo que llegue aca
# sin el repositorio deja de dejar entrar, con `503 demo access codes not
# configured`. En la instancia de un cliente no hay demo que abrir.
if demo_username():
    app.state.demo_codigos = DemoCodigoRepository(db_usuarios.sessions())

# ── Auditoria de clientes (libracore v1.157.0, ADR-043) ──────────────────────
#
# Las escrituras de `clients` (`/api/clientes`, el fiado, la ficha) son del motor de core y le avisan a este registrador
# dentro de la misma transaccion: si el INSERT del log falla, se cae la escritura entera. El registrador es el
# `registrador_dbapi` de libraauth, que arma la fila con el formato de siempre y escribe en `actividad_log` (la tabla la
# crea `init_schema` de libracommerce, en la misma base que el motor). La pantalla de Logs la muestra como tipo
# `actividad` ("Cambios"), sin pantalla nueva.
#
# El usuario sale del `ContextVar` `usuario_actual` de libraauth, que llena `agregar_middleware_de_usuario` leyendo la
# cookie firmada de `app.state.session_auth` (puesto arriba). Sin el middleware la fila diria «Sistema» y no se
# notaria: por eso hay un test (`tests/test_clientes_auditados.py`) que mira el usuario. Se configura al importar el
# modulo, como `app.state`: el registrador es un callable y la conexion se resuelve en cada escritura.
auditoria_del_motor.configurar_auditoria(registrador_dbapi({"clients": "cliente"}))
agregar_middleware_de_usuario(app)


_BYPASS_PATHS = {"/suspendido", "/favicon.ico", "/api/auth/verify", "/health"}

def _leer_estado_del_request(username: str | None) -> dict:
    """Todo lo que el middleware lee de la base y del disco, en un solo viaje.

    🔴 **Corre en el threadpool y no en el loop**, y por una razón que se
    multiplica: el middleware atiende TODOS los requests. Con un solo proceso
    de uvicorn, estas cuatro lecturas sincrónicas —el usuario, `config.json`,
    los módulos y los pagos de MP pendientes— frenaban el loop entero mientras
    duraban, así que una base lenta demoraba a todos los requests a la vez,
    `/health` incluido. Un solo `run_in_threadpool` y no cuatro: el salto al
    hilo se paga una vez.

    Los `try` son los mismos que había inline y fallan igual: el usuario
    propaga —un 500, como antes— y el resto cae a su default.
    """
    estado = {
        "current_user": db.get_usuario_by_username(username) if username else None,
    }
    try:
        cfg = config_manager.load()
        estado["empresa_nombre"]   = cfg.get("empresa_nombre", "")
        estado["servicio_estado"]  = cfg.get("servicio_estado", "activo")
        estado["servicio_mensaje"] = cfg.get("servicio_mensaje", "")
    except Exception:
        estado["empresa_nombre"]   = ""
        estado["servicio_estado"]  = "activo"
        estado["servicio_mensaje"] = ""
    try:
        mods = db.get_modulos()
        estado["modulos"] = {m for m, on in mods.items() if on}
    except Exception:
        estado["modulos"] = set()
    try:
        estado["mp_pending_count"] = db.get_mp_pending_count()
    except Exception:
        estado["mp_pending_count"] = 0
    return estado


class CurrentUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/static"):
            return await call_next(request)
        # Leer la cookie firmada es CPU y nada más: se queda en el loop.
        username = get_current_user(request)
        estado = await run_in_threadpool(_leer_estado_del_request, username)
        for clave, valor in estado.items():
            setattr(request.state, clave, valor)

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
# El registro de errores de la familia (ADR-045 de libracore): un 500 deja una linea en `DATA_DIR/errores/` con un `ref`
# que el usuario puede dictar, y monta `POST /api/errores-cliente` para los errores del navegador (publico a proposito).
instalar_registro_de_errores(app, "contalibra")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# 🔑 **`GET` y `HEAD`.** Un monitor de uptime (uptime-kuma) sondea con `HEAD`, y
# `@app.get` a secas lo contestaba con 405: la instancia figuraba caída estando
# sana. FastAPI no deriva el `HEAD` del `GET`.
@app.api_route("/health", methods=["GET", "HEAD"], include_in_schema=False)
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
# El autocompletado del punto de venta (`GET /productos/buscar`) es del motor
# (P9-M2); la sesion la exige el propio endpoint, como el router historico.
app.include_router(build_buscar_productos_router(
    conexion=_abrir_conexion, usuario_actual=require_auth, solo_vendibles=False,
))
app.include_router(ventas_router.router)
# Los exports CSV y REGINFO fuera de `/api/` son del motor (P9-M4), con la
# misma sesion por cookie y el mismo gate que tenian los routers propios:
# logs y libros IVA solo admin, reportes cualquier usuario.
app.include_router(build_logs_export_router(
    solo_admin=require_admin, nombre_archivo="logs_contalibra.csv", actividad=db.get_actividad_log,
))
app.include_router(build_reportes_export_router(sesion=require_auth, reportes=REPORTES))
app.include_router(build_libros_iva_export_router(solo_admin=require_role("admin")))

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
# `GET /api/terminos`, `POST /api/terminos/aceptar`, `GET /api/terminos/historial`.
# Bajo `/api` como el resto de la API de este producto, y **sin gatear desde
# afuera**: es el unico camino para salir del gate.
app.include_router(build_terminos_router(prefix="/api/terminos"))
app.include_router(build_dashboard_router(usuario_actual=get_current_user_json))
# `resumen` también gatea adentro, con su propia dependencia: acepta la
# credencial del panel del dueño, que no es usuario de esta instancia y por lo
# tanto no pasaría `_auth_json`.
app.include_router(api_resumen_router.router)
app.include_router(
    # Clientes, proveedores, egresos, tesoreria, cuenta corriente, reportes,
    # libros IVA y logs son factories de LibraCore desde P9-M4; el gate (auth +
    # modulo) sigue declarado aca.
    build_clientes_router(),
    dependencies=[_auth_json, Depends(require_module("clientes"))],
)
# Add-on mayorista: comparte el prefijo `/api/clientes` pero su gate es el del
# add-on, no el de `clientes` (ver plans.py::ADDONS). Sus rutas
# (`/{id}/lista-precio`) no chocan con las del router de clientes. Factory del
# motor desde el 2026-09-28 (ADR-010 de libracommerce): reemplaza a
# `app/web/api/mayorista.py`, retirado.
app.include_router(
    build_cliente_lista_router(conexion=_abrir_conexion),
    dependencies=[_auth_json, Depends(require_module("mayorista"))],
)
# Quiebres por cantidad y resolución de precio por cantidad. Mismo prefijo
# `/api/listas-precio` que el router base, pero gateado por el add-on.
app.include_router(
    build_quiebres_router(conexion=_abrir_conexion),
    dependencies=[_auth_json, Depends(require_module("mayorista"))],
)
app.include_router(
    build_productos_router(conexion=_abrir_conexion, usuario_actual=get_current_user_json),
    dependencies=[_auth_json, Depends(require_module("productos"))],
)
app.include_router(
    build_listas_precio_router(conexion=_abrir_conexion),
    dependencies=[_auth_json, Depends(require_module("listas_precio"))],
)
app.include_router(
    build_proveedores_router(),
    dependencies=[_auth_json, Depends(require_module("proveedores"))],
)
app.include_router(
    build_egresos_router(usuario_actual=get_current_user_json),
    dependencies=[_auth_json, Depends(require_module("egresos"))],
)
# El guard (admin de la instancia O token de servicio -- lo que le permite al
# backoffice de la suite, admin.contalibra.com.ar, administrar los usuarios
# de esta instancia sin ser usuario de ella) ya va DENTRO del router: se lo
# pasa como `admin_guard` a `build_users_router()` (ver
# `app/web/api/usuarios.py`), no acá -- una sola dependencia y no dos
# ejecutando lo mismo por request.
app.include_router(api_usuarios_router.router)
# Consultas que llegan desde otro producto de la familia (lo estrena MedLibra).
#
# 🔴 **Sin dependencia acá**: el router gatea adentro, y con DOS niveles
# distintos a propósito. `/consultas` acepta la credencial de integración —es lo
# que usa el producto emisor, que no es usuario de esta instancia— y el token de
# servicio, pero `/config`
# exige **admin de la instancia**: quién recibe las ventas externas lo decide
# quien es dueño de la caja, no quien tiene el token. Colgar acá una
# dependencia única aplanaría esa diferencia.
app.include_router(api_integraciones_router.router)
app.include_router(
    # Solo el correo saliente, no todo `/api/config` — ver el comentario en
    # web/api/config.py sobre por que es un router aparte.
    api_config_router.smtp_router,
    dependencies=[Depends(require_admin_o_servicio_json)],
)
app.include_router(
    # `POST /api/config/smtp/probar`, del motor (libracore v1.69.0). Reemplaza
    # al `GET /api/email/probar` que este producto tenia escrito a mano, y que
    # se retiro en el mismo cambio: era uno de los dos unicos productos que
    # podian probar su correo, y ahora el boton sale del kit y lo tienen los
    # ocho.
    #
    # 🔑 Sigue resolviendo por `smtp_efectivo` sobre el MISMO resolver que los
    # envios, que es lo que hacia que el boton significara algo. El prefijo es
    # el que este producto ya publico.
    build_smtp_probe_router(db_usuarios.smtp_config, prefix="/api/config/smtp"),
    dependencies=[Depends(require_admin_o_servicio_json)],
)
app.include_router(
    api_config_router.router,
    dependencies=[Depends(require_admin_json)],
)
# Datos de la empresa y logo, del motor. Reemplazan al `GET /api/config`
# --que devolvia `config_manager.load()` ENTERO, o sea el token de MercadoPago
# y la contrasena de SMTP en el JSON de una pantalla--, al `PUT /api/config/empresa`
# y al `POST /api/config/empresa/logo` propios.
#
# La lectura va con el mismo gate que la escritura y no mas abierta: es la
# convencion de esta instancia, donde `/api/config` entero es admin.
#
# 🔑 El del motor ademas BORRA los logos anteriores al subir uno nuevo. El
# propio no: dejaba convivir `logo.png` y `logo.jpg`, y `resolve_logo_path`
# elige por fecha de modificacion cuando el path guardado no existe --o sea que
# el logo viejo puede volver solo, en el comprobante.
app.include_router(build_empresa_router(), dependencies=[Depends(require_admin_json)])
app.include_router(build_empresa_admin_router(), dependencies=[Depends(require_admin_json)])

# El tema de la suite (libracore ADR-012, libra-ui ADR-007/008): los colores que el backoffice de la suite empuja a esta instancia. La
# lectura es PÚBLICA a propósito (el login también va con los colores de la suite y no expone nada sensible). La escritura es del admin O
# del token de servicio del backoffice: 🔴 con `require_admin_json` a secas el backoffice NO entraría (esa guarda no conoce el token).
app.include_router(build_tema_router())
app.include_router(build_tema_admin_router(), dependencies=[Depends(require_admin_o_servicio_json)])
# Los adicionales contratados (libracore ADR-048): `GET /api/adicionales` lo ve el admin o el backoffice; `PUT /api/adicionales/{clave}` SOLO el token
# de servicio (🔴 un adicional es un limite comercial: si lo cargara el admin del cliente, contratar no costaria nada). Desde E6 de LibraEdge
# (2026-10-19) el catalogo de `plans.ADICIONALES` tiene `offline`, que se mide en sucursales DISTINTAS con un nodo activo: es lo que cobra y lo que
# hace cumplir `libraedge-central nodo registrar` (`app/offline.py`). `mayorista` y `resguardo_externo` (`plans.ADDONS`) aparecen como si/no.
app.include_router(build_adicionales_router(
    require_admin_o_servicio_json, require_solo_servicio_json, medir={"offline": sucursales_con_nodo},
    leer_modulos=db.get_modulos, escribir_modulo=db.set_addon,
))
# La sincronizacion del nodo offline de LibraEdge (E6): `/sync/v1/push`, `/sync/v1/pull` y `/sync/v1/ticket-arca`. Se
# monta siempre: sin un nodo registrado no hay ningun secreto valido y todo contesta 401 (ver el docstring del router).
app.include_router(sincronizacion_offline.router)
# «Sucursal sin internet» (libraedge ADR-011, libra-ui ADR-080): el admin da de alta el nodo de una sucursal y descarga su
# carga (`carga-nodo-….json`, con el secreto del nodo: sólo viaja como adjunto de ese POST), ve los nodos y los da de baja.
# Toda la lógica es de LibraEdge (las mismas funciones que `libraedge-central nodo registrar --carga`); acá sólo la guarda
# de admin y el aprovisionamiento de este producto (`app/offline.py`). El adicional `offline` lo hace cumplir el alta.
app.include_router(
    create_nodos_router(aprovisionamiento_offline, _abrir_conexion),
    dependencies=[Depends(require_admin_json)],
)
# MercadoPago, del motor. Reemplaza al `PUT /api/config/mp` propio.
#
# 🔴 Lo que cambia y no es cosmetico: el token vuelve ENMASCARADO. El
# `GET /api/config` que se va lo devolvia entero, y con el la contrasena de
# SMTP. Ademas suma el boton que le pregunta a MercadoPago si el token sirve, y
# una puerta para desconectar la cuenta --con "vacio = no lo toques" no habia
# otra forma.
app.include_router(
    build_mp_config_router(prefix="/api/config/mercadopago"),
    dependencies=[Depends(require_admin_json)],
)
# ARCA, del motor. Reemplaza al `PUT /api/config/arca` y al
# `POST /api/config/arca/certificados` propios, y a los tres `GET /api/arca/*`
# que vivian mas abajo en este archivo.
#
# 🔑 Lo que gana la pantalla: el par se valida ANTES de guardarse. Subir el
# `.csr` en vez del `.crt`, cambiar de campo el certificado y la clave, o subir
# un par que **no es pareja** se rechazan al subir, con el motivo escrito. Antes
# los tres se aceptaban y fallaban al emitir el primer comprobante.
app.include_router(
    build_arca_router(prefix="/api/config/arca"),
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
# Enlace de la copia externa con la nube del cliente (LibraCore v1.93.0): el
# cliente conecta su Google Drive o Dropbox desde Configuracion -> Datos /
# Backup, y el subidor del host usa el `rclone.conf` que queda en
# `<BACKUPS_DIR>/.resguardo/`. Por eso va el MISMO directorio que el router de
# backup de arriba: es de ahi de donde el host lee la instancia.
#
# Dos gates, los dos necesarios:
#   - `require_admin_json`: conectar la nube es configuracion, como el resto de
#     la pestana. Tambien cubre el `/callback`, a proposito (ver el docstring
#     del motor: la cookie es `SameSite=Lax` y viaja en la vuelta del OAuth).
#   - `require_module("resguardo_externo")`: es un ADD-ON (`plans.ADDONS`), no
#     parte de un plan. Arranca apagado y lo prende el backoffice por
#     instancia; una fila que falta en `modulos` tambien da 403, que libra-ui
#     muestra como "sin plan".
#
# `volver_a` apunta a `/config` y no al `/configuracion` del default del motor:
# en este producto la pantalla de Configuracion vive en `/config`
# (`frontend/src/App.tsx`).
app.include_router(
    build_resguardo_enlace_router(
        config_router.BACKUPS_DIR,
        carpeta="Resguardo Contalibra",
        volver_a="/config?seccion=datos",
    ),
    dependencies=[Depends(require_admin_json), Depends(require_module("resguardo_externo"))],
)
app.include_router(
    # `sucursal_por_defecto`: un depósito nuevo cae en «Casa central» (la sucursal única, `app/sucursal_unica.py`) y
    # no queda huérfano. Nada visible: no hay pantalla de sucursales (F2 no se expone hasta que un cliente la pida).
    build_depositos_router(
        conexion=_abrir_conexion, usuario_actual=get_current_user_json,
        opciones=OpcionesDepositos(sucursal_por_defecto=True),
    ),
    dependencies=[_auth_json, Depends(require_module("depositos"))],
)
app.include_router(
    build_stock_router(conexion=_abrir_conexion, usuario_actual=get_current_user_json),
    dependencies=[_auth_json, Depends(require_module("stock"))],
)
app.include_router(
    # Los debitos por venta salen de `sales` (LibraCommerce), no de `ventas`.
    # `con_recibos`: al cobrar se emite el recibo de cobranza y al borrar el pago
    # se anula. Es lo que este producto hacia por su cuenta.
    build_cuenta_corriente_router(
        usuario_actual=get_current_user_json, solo_admin=require_admin_json,
        origen=VENTAS_LIBRACOMMERCE, con_recibos=True,
    ),
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
    build_tesoreria_router(usuario_actual=get_current_user_json),
    dependencies=[Depends(require_admin_json), Depends(require_module("tesoreria"))],
)
app.include_router(
    build_caja_router(usuario_actual=get_current_user_json),
    dependencies=[_auth_json, Depends(require_module("caja"))],
)
app.include_router(
    # `sucursal_por_defecto` (libracore ADR-062): una caja creada sin `sucursal_id` nace en «Casa central», como el
    # depósito de arriba, y no queda en NULL hasta el próximo arranque (`app/sucursal_unica.py`).
    build_cajas_router(opciones=OpcionesCajas(sucursal_por_defecto=sucursal_predeterminada)),
    dependencies=[_auth_json, Depends(require_module("cajas"))],
)
app.include_router(
    # El resumen y el cierre son de `db_turnos`: leen `sales`, no la tabla
    # `ventas` de LibraCore (P9-M3).
    build_turnos_router(
        usuario_actual=get_current_user_json,
        resumen_turno=db.get_resumen_turno, cerrar_turno=db.cerrar_turno,
    ),
    dependencies=[_auth_json],
)
# El detalle con `factura_pendiente` (nodo offline, libracore ADR-074) va ANTES que el router del motor: gana el mismo
# `GET /api/ventas/{id}`. Fuera de un nodo devuelve lo mismo que el del motor, con `factura_pendiente: null`.
app.include_router(
    api_ventas_router.detalle,
    dependencies=[_auth_json, Depends(require_module("ventas"))],
)
app.include_router(
    api_ventas_router.router,
    dependencies=[_auth_json, Depends(require_module("ventas"))],
)
# La factura desde la venta y el cobro por QR (LibraCore), con el mismo prefijo
# y el mismo gate que el punto de venta (P9-M3).
app.include_router(
    api_ventas_router.cobro,
    dependencies=[_auth_json, Depends(require_module("ventas"))],
)
app.include_router(api_ventas_router.cobro_legado, dependencies=[_auth_json])
# La facturacion del nodo offline (libracore ADR-074): `/api/nodo/conexion` y `/api/nodo/facturar-pendientes`, con el
# mismo gate que el cobro. Fuera de un nodo contestan `es_nodo: false` y no hacen nada.
app.include_router(
    api_ventas_router.nodo,
    dependencies=[_auth_json, Depends(require_module("ventas"))],
)
# La barra de estado del pie (libracore ADR-075, libra-ui ADR-083): LibraEdge (el nodo con su bandeja, o los nodos del
# central), usuario, versión, el certificado de ARCA y el último respaldo, en una consulta. Cualquier usuario logueado; lo
# que ve cada rol lo decide el motor (ARCA y respaldo, sólo admin). Sin `require_module`: la barra es de todas las pantallas.
app.include_router(build_estado_del_sistema_router(
    usuario_actual=get_current_user_json, ventas=venta_facturacion.PUERTO,
    nodos_del_central=nodos_del_central, backups_dir=config_router.BACKUPS_DIR,
))
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
    build_libros_iva_router(),
    dependencies=[Depends(require_admin_json), Depends(require_module("libros_iva"))],
)
app.include_router(
    # Ventas, medios, productos, stock bajo y resumen salen de `sales`: el
    # puerto es `libracommerce.erp.reportes` (ver db_reportes.py).
    build_reportes_router(reportes=REPORTES),
    dependencies=[_auth_json, Depends(require_module("reportes"))],
)
app.include_router(
    # La tabla de usuarios la declara libraauth y las partes de ventas y stock
    # de la linea de tiempo leen `sales`/`stock_movements`: los tres van como
    # puertos (ver db_logs.py).
    build_logs_router(
        usuarios=db.get_all_usuarios, actividad=db.get_actividad_log,
        actividad_count=db.get_actividad_count,
    ),
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
    # Lo deposita otro sistema, sin humano detrás: la instancia que llama
    # presenta el `LIBRA_INTEGRACION_TOKEN` de ésta (libraauth v0.52.0). Guard
    # propio y no el de Usuarios: la integración no abre usuarios, SMTP ni tema.
    # Admin y backoffice siguen entrando como antes.
    build_comprobantes_ingesta_router(),
    dependencies=[Depends(require_admin_o_servicio_o_integracion_json)],
)
app.include_router(
    # La bandeja la trabaja una persona, y decide facturar: sólo admin.
    build_comprobantes_bandeja_router(usuario_actual=_quien_resolvio),
    dependencies=[Depends(require_admin_json)],
)


@app.on_event("startup")
def startup():
    # 🔴 De a un proceso por vez (ADR-044 de libracore). Con `uvicorn --workers N` cada worker corre este hook, y
    # «si no existe, crear» (el admin, el usuario de la demo, el depósito por defecto) se contestaba «no existe» en
    # todos antes de que ninguno creara. El candado hace que el segundo espere al primero y vea lo que dejó; cada
    # paso sigue preguntando adentro (`repo.list()`, `SELECT 1 FROM locations`...), así que sigue siendo idempotente.
    with una_vez_al_arrancar("contalibra-arranque"):
        db.init_db()
        # 🔴 La cadena de LibraAuth tiene que haber corrido (libraauth v0.45.0). Si no,
        # la app no arranca y el error dice el comando. Reemplaza al `create_all()` que
        # `app/db_usuarios.py` corría al importarse. Va después de `init_db()` y antes
        # de sembrar usuarios, que es lo primero que toca esas tablas.
        exigir_schema_al_dia(db_usuarios._engine, prefijo="contalibra", base="dominio")
        db.ensure_admin_user()
        # No-op salvo que la instancia sea una demo (DEMO_MODE + DEMO_USERNAME).
        db.ensure_demo_user()
        # Saca de `config.json` los secretos que quedaron en claro (2026-09-17). Va
        # DESPUES de `exigir_schema_al_dia`: la tabla `secretos_instancia` es de la
        # revision `0002` de libraauth, y escribir en ella antes de saber que existe
        # convertiria un schema viejo en un 500 en vez del error que dice el comando.
        # Idempotente: la segunda vez no hace nada.
        db_usuarios.migrar_secretos()

    # Nodo offline (libracore ADR-074, libracommerce ADR-068): la bandeja de comprobantes pendientes se factura sola al
    # volver la conexión, y en cada vuelta se encola la `venta.facturada` que `al_facturar` no llegó a encolar. Fuera de
    # un nodo (Compulibra, la demo) no arranca nada. Con varios workers cada uno arranca el suyo: el candado por venta
    # evita la doble factura.
    global _parar_facturacion_al_volver
    from libracommerce.erp.offline import reconciliador
    from libracore.venta_facturacion import arrancar_facturacion_al_volver

    from app import venta_facturacion
    from app.offline import OUTBOX

    _parar_facturacion_al_volver = arrancar_facturacion_al_volver(
        venta_facturacion.PUERTO, en_cada_vuelta=reconciliador(OUTBOX, _abrir_conexion),
    )


_parar_facturacion_al_volver = None


@app.on_event("shutdown")
def parar_facturacion_al_volver():
    if _parar_facturacion_al_volver is not None:
        _parar_facturacion_al_volver.set()


# `GET` y `HEAD`: la raíz que redirige tiene que dar lo mismo para los dos (ver `/health`).
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
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

    # Sigue siendo `async` por el `await request.json()` de arriba, pero esto
    # va al threadpool: es una consulta a la base **más el hash de la
    # contraseña**, que es lento a propósito. Inline, con un solo proceso de
    # uvicorn, cada intento de login de la landing frenaba a toda la instancia.
    user = await run_in_threadpool(db.check_usuario_credentials, username, password)
    if not user:
        return JSONResponse({"valid": False})

    return JSONResponse({
        "valid": True,
        "nombre_empresa": request.state.empresa_nombre,
    })


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


# Consulta de CUIT en el padrón de ARCA: el router del motor (`libracore.consultar_cuit_router`,
# extraído de este mismo handler). `GET /api/consultar-cuit/{cuit}`, con la misma sesión por cookie.
# 🔴 Con `get_current_user_json` y no con `require_auth`: es un fetch del kit, y sin sesión
# `require_auth` contesta 307 a /login (el fetch lo sigue y recibe el HTML del login); la dependencia
# JSON contesta 401, como el resto de `/api`.
app.include_router(build_consultar_cuit_router(usuario_actual=get_current_user_json))


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
    montar_spa(app, FRONTEND_DIST)
