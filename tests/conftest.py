"""Infraestructura de la suite de Contalibra.

La app entera se aisla con UNA variable: `DATA_DIR` (db_core.py y
libracore.config_manager resuelven todas sus rutas desde ahi EN IMPORT
TIME). Por eso este archivo la setea a un directorio temporal ANTES de
importar cualquier modulo del producto -- importar primero y setear
despues dejaria la suite corriendo contra `contalibra.db` real, que es
exactamente el accidente que este archivo existe para impedir.

El proceso de pytest tiene un solo DATA_DIR (los modulos congelan las
rutas al importarse), asi que el aislamiento POR TEST no es "otro
directorio" sino "misma ruta, base recreada": la fixture `client`
dispone el engine de SQLAlchemy (db_usuarios lo fija en import), deja la
base como nueva y deja que el evento startup de web/app.py (init_db +
ensure_admin_user) corra sobre ella.

Con `pytest -n 4` cada worker es un proceso con su propio DATA_DIR y su propia
base de PostgreSQL, y la base "como nueva" sale de una plantilla: ver mas abajo
"Una base por worker, restaurada desde una plantilla".
"""

# --- Zona horaria de la suite ---------------------------------------------
# Argentina, UTC-3 fijo, sin horario de verano. Se fija ACA y no se hereda de
# la maquina: el CI y WSL corren en UTC, asi que un test que compare una
# fecha da distinto segun donde se corra, y a las 21:00 de Argentina el
# `date.today()` del proceso ya devuelve manana. Antes de cualquier import
# del producto, porque `tzset()` no alcanza a lo ya importado.
import os as _os
import time as _time

_os.environ["TZ"] = "America/Argentina/Buenos_Aires"
_time.tzset()

import os
import sys
import tempfile

# --- Entorno ANTES de tocar ningun import del producto -------------------
_TMP = tempfile.mkdtemp(prefix="contalibra-tests-")
os.environ["DATA_DIR"] = _TMP

# --- El motor: PostgreSQL y nada mas -------------------------------------
#
# 🔴 Sin esto la suite CAE A SQLITE en silencio: `db_core.py` deriva `DB_PATH`
# de `DATA_DIR` y arma una ruta a un archivo, y `libracore.db.core.configure()`
# decide el motor con `"://" in db_path` — sin URL, SQLite. La suite quedaba
# verde y no decia nada del motor real.
#
# El modo SQLite se retiro el 2026-08-12 para toda la familia: los productos
# corren sobre PostgreSQL y una suite verde sobre SQLite no chequea las FK, no
# valida los tipos y acepta cadenas donde la base pide enteros. Los defectos
# que PostgreSQL rechaza de entrada llegaban a produccion.
#
# El CI corria la suite DOS veces —una sin URL, o sea SQLite, y otra con
# PostgreSQL— y la primera se saco junto con este guard. Es el mismo criterio
# que LibraDesk aplica desde el 2026-08-12.
if not os.environ.get("CONTALIBRA_DATABASE_URL"):
    raise RuntimeError(
        "La suite de Contalibra necesita PostgreSQL: defini "
        "CONTALIBRA_DATABASE_URL (ej. "
        "postgresql://contalibra:contalibra-ci@localhost:5432/contalibra). "
        "Sin esa variable la suite correria sobre SQLite, que es lo que se "
        "retiro el 2026-08-12: una suite verde sobre SQLite no dice nada "
        "sobre el motor real."
    )

# --- Una base por worker, restaurada desde una plantilla --------------------
#
# Cada test arranca de una base **nueva**, y rearmarla era lo que mas costaba:
# medido sobre PostgreSQL 16, entre 1,7 y 3,5 s por test que usa `client`, casi
# todo en `init_db()` sobre una base vacia (1,1 a 2,8 s) y en la cadena de
# libraauth (0,2 a 0,7 s); vaciar el schema eran 0,1 s y el login 0,12 s. Con
# `CREATE DATABASE ... TEMPLATE` la base sale de una copia ya armada, ~0,1 s, y
# el `startup` que corre despues sobre ella es el de un reinicio (`init_db()`
# idempotente, 0,15 s). El mecanismo (una base por worker de xdist, plantillas,
# `FORCE` para echar las conexiones del test anterior) vive en
# `libracore.testing.pg_por_worker`; aca queda lo propio de Contalibra: que hay
# en cada plantilla.
#
# La URL del worker se pasa al resto de la suite pisando `CONTALIBRA_DATABASE_URL`
# ANTES de importar `app`: `db_core.DB_PATH` la lee al importarse, y de ahi salen
# `db_usuarios._engine`, `libracore.db.core` y todos los tests que componen algo
# con `db_core.DB_PATH`. Los scripts que los tests lanzan por `subprocess`
# (`libracore-migrar`, `alembic`) heredan el entorno, asi que ven la del worker.
from libracore.testing.pg_por_worker import base_por_worker  # noqa: E402

_PG = base_por_worker("contalibra", os.environ["CONTALIBRA_DATABASE_URL"])
os.environ["CONTALIBRA_DATABASE_URL"] = _PG.url

# SessionAuth (libraauth) exige SECRET_KEY fuera de development y la app
# no levanta sin el. Un valor fijo ademas hace deterministas las cookies.
os.environ["SECRET_KEY"] = "suite-secret-no-productivo"
# ensure_admin_user usa ADMIN_PASSWORD; sin ella genera una aleatoria y
# la suite no podria loguearse.
os.environ["ADMIN_PASSWORD"] = "admin-suite-1234"
os.environ["DOCS_AUTH_SECRET"] = "docs-secret-suite"
# Con ENV=development libracore.arca_facturacion usa numeracion local y
# CAE simulado (_es_dev) -- el mismo camino que corre dev.contalibra, asi
# que la suite ejerce el flujo de facturacion completo sin tocar ARCA.
os.environ["ENV"] = "development"

# La raiz del repo va al sys.path por `plans.py`, que quedo AFUERA del
# paquete a proposito: libracore lo importa por nombre (`import plans`), y
# `apply_plan` pasa por ahi. El paquete `app` en si no lo necesita -- se
# instala con `pip install -e ".[dev]"` como el resto de la familia.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import libraauth.session_auth as _session_auth
import pytest
from fastapi.testclient import TestClient
from libraauth.testing import crear_schema_de_auth

from app import database as db  # noqa: F401  (re-exporta todo el dominio)
from app import db_core, db_usuarios
from app.web.app import app

ADMIN_USER = "admin"
ADMIN_PASS = os.environ["ADMIN_PASSWORD"]


# Dos plantillas por worker, armadas la primera vez que se piden:
#
# - **vacia**: `public` recien creado y la cadena de libraauth. Es EXACTAMENTE lo
#   que dejaba antes `_reset_data_dir()` (`DROP SCHEMA` + `CREATE SCHEMA` +
#   `crear_schema_de_auth`), asi que los tests que prueban el arranque o las
#   migraciones desde cero (`test_arranque_exige_cadena_libraauth`,
#   `test_schema_propio_congelado`, `test_demo_publica`) ven el mismo estado de
#   partida que siempre.
# - **armada**: la vacia mas lo que le hace el evento `startup` (`init_db` y el
#   admin de bootstrap). Es solo para la fixture `client`, que despues vuelve a
#   correr `startup` sobre ella: es lo que el producto hace en cada reinicio.
#
# Que NO cambia: ningun test ve una base distinta de la de antes, solo que la
# primera mitad del arranque ya esta hecha.


def _construir_vacia(url: str) -> None:
    """Plantilla "vacia": el schema de auth sobre una base sin nada mas."""
    crear_schema_de_auth(url)


def _construir_armada(url: str) -> None:
    """Plantilla "armada": la vacia y el `startup` real de la app, corrido contra `url`.

    La app esta atada a la base del WORKER (`db_core.DB_PATH`), no a la de la
    plantilla, asi que mientras dura el armado se apunta a `url` lo que la ata:
    el engine de `db_usuarios` (que `startup` lee por nombre de modulo, y del que
    cuelga el `sessionmaker` de todos los repositorios de auth) y la conexion de
    `libracore.db.core`. Al terminar se vuelve a dejar todo como estaba, aunque
    falle.

    Se arma con el entorno de la suite y sin el de la demo: si el primer test del
    worker que pide `client` tuviera `DEMO_MODE` puesto, la plantilla sembraria al
    visitante y la veria cualquier test posterior. El `startup` que corre cada
    test sobre la copia se encarga de lo que ese test haya pedido.
    """
    from libracore.db import core
    from sqlalchemy import create_engine, pool

    from app.web.app import startup

    _construir_vacia(url)
    motor = create_engine(url.replace("postgresql://", "postgresql+psycopg://", 1), poolclass=pool.NullPool)
    del_worker = db_usuarios._engine
    mp = pytest.MonkeyPatch()
    mp.delenv("DEMO_MODE", raising=False)
    mp.delenv("DEMO_USERNAME", raising=False)
    mp.setattr(db_usuarios, "_engine", motor)
    db_usuarios._sessions.configure(bind=motor)
    core.configure(url)
    try:
        startup()
    finally:
        motor.dispose()
        db_usuarios._sessions.configure(bind=del_worker)
        core.configure(db_core.DB_PATH)
        mp.undo()


def _reset_data_dir(plantilla: str = "vacia"):
    """Base y config de cero, misma ruta (o mismo schema).

    `plantilla`: de cual de las dos copiar la base ("vacia", la que dejaba
    siempre este helper, o "armada", para `client`).

    El dispose es obligatorio: el engine de db_usuarios tiene un pool de
    conexiones abiertas sobre la base; restaurarla se las lleva por delante
    (`DROP DATABASE ... FORCE`) y el pool las seguiria entregando muertas.
    """
    db_usuarios._engine.dispose()
    if db_core.ES_POSTGRES:
        _PG.restaurar(plantilla, {"vacia": _construir_vacia, "armada": _construir_armada}[plantilla])
    else:
        for suffix in ("", "-wal", "-shm"):
            path = db_core.DB_PATH + suffix
            if os.path.exists(path):
                os.unlink(path)
        crear_schema_de_auth(db_usuarios._engine)
    config_json = os.path.join(_TMP, "config.json")
    if os.path.exists(config_json):
        os.unlink(config_json)
    # 🔴 Y los certificados de ARCA, que hasta el 2026-08-24 SOBREVIVIAN al
    # reset. El proceso de pytest tiene un solo DATA_DIR, asi que el par que
    # dejaba un test se lo encontraba el siguiente --- y desde que el router
    # del motor chequea que certificado y clave sean pareja, ese resto hace
    # que la subida del test siguiente se rechace con 422. El sintoma no se
    # parece a la causa: el test falla diciendo "no esta configurado".
    certs = os.path.join(_TMP, "arca_certs")
    if os.path.isdir(certs):
        for nombre in os.listdir(certs):
            try:
                os.unlink(os.path.join(certs, nombre))
            except OSError:
                pass


@pytest.fixture()
def client():
    """TestClient contra una base recien creada.

    El `with` importa: dispara el evento startup (init_db +
    ensure_admin_user), que es el mismo camino de arranque del contenedor
    real -- la suite no inicializa el schema por su cuenta a proposito,
    para que un schema que no levanta se vea aca y no en el deploy.
    """
    _reset_data_dir("armada")
    # base_url https: la cookie de sesion es secure=True y sobre http el
    # cliente no la reenvia -- todos los requests darian 401 (misma trampa
    # ya documentada en el portal de pacientes del PACS).
    with TestClient(app, base_url="https://testserver") as c:
        yield c


@pytest.fixture()
def admin_client(client):
    """Cliente ya logueado como el admin que crea ensure_admin_user."""
    resp = client.post("/api/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    assert resp.status_code == 200, f"login admin fallo: {resp.status_code} {resp.text}"
    return client


# ── Términos y Condiciones: aceptados para el resto de la suite ─────────────
#
# Desde libraauth v0.31.0 el motor corta con 403 **cualquier** llamada gateada
# por rol mientras la instancia no haya aceptado la versión vigente del
# contrato. Sin esta excepción, la suite entera se pone roja de golpe: cada
# test que loguea y pide datos recibe el 403 del gate en vez de lo que iba a
# medir, y el rojo no dice nada sobre el dominio.
#
# 🔴 **Esto NO apaga el gate donde importa.** El corte tiene su propio archivo,
# `test_terminos_gate.py`, que se marca con `sin_aceptar_terminos` y queda
# afuera de esta excepción. Si alguien borrara el cableado de
# `app.state.terminos`, esa marca es lo único que se pondría rojo.


@pytest.fixture(autouse=True)
def _terminos_ya_aceptados(request):
    if request.node.get_closest_marker("sin_aceptar_terminos"):
        yield
        return

    from libraauth.terminos import TerminosRepository

    # 🔴 **`MonkeyPatch()` propio y no el fixture `monkeypatch`.** El fixture es
    # uno solo por test y lo comparten todas las fixtures que lo pidan, asi que
    # un `monkeypatch.undo()` en el cuerpo de un test —que existe, y es
    # legitimo— deshace TAMBIEN este parche y le prende el gate a la mitad del
    # test. El sintoma no se parece a la causa: la llamada siguiente devuelve
    # 403 y el test explota con un `KeyError` sobre la clave que esperaba en el
    # JSON. Lo encontro `test_despues_de_un_fallo_el_boton_puede_emitirlo` de
    # VentaLibra.
    mp = pytest.MonkeyPatch()
    mp.setattr(TerminosRepository, "esta_aceptada", lambda self: True)
    yield
    mp.undo()


# ── Captcha ALTCHA: aprobado para el resto de la suite ─────────────────────
#
# Desde libraauth v0.40.0 este producto monta el router con `captcha=True`:
# el login y el forgot-password exigen la solucion de un desafio. La suite
# postea a `/api/login` en muchos lugares (el fixture `admin_client`, los tests
# de usuarios, de la demo, del reset de contrasena...) y resolver un desafio en
# cada uno no prueba nada de este producto.
#
# 🔴 **El captcha lo prueba libraauth; aca solo se cablea.** Lo que es de este
# producto —que la ruta exista, que un login sin captcha rebote— lo fija
# `test_captcha_login.py`, que restaura la funcion real con
# `_CAPTCHA_DE_ORIGINAL`. Si alguien sacara `captcha=True` del router, ese
# archivo es lo que se pondria rojo.

#: La funcion real, para que un test pueda volver a ponerla.
_CAPTCHA_DE_ORIGINAL = _session_auth._captcha_de


class _CaptchaQueAprueba:
    """Doble del `Captcha` de libraauth: aprueba cualquier payload.

    `emitir()` delega en un `Captcha` real y barato, para que `GET
    /api/captcha` siga devolviendo un desafio con la forma de siempre.
    """

    def __init__(self):
        from libraauth.captcha import Captcha

        self._real = Captcha("clave-de-prueba", costo=1, contador_min=1, contador_rango=5)

    def emitir(self) -> dict:
        return self._real.emitir()

    def verificar(self, payload) -> bool:
        return True


_CAPTCHA_DE_PRUEBA = _CaptchaQueAprueba()


@pytest.fixture(autouse=True)
def _captcha_aprobado(monkeypatch):
    """Todo login y forgot-password de la suite pasa el captcha.

    Se parchea la funcion de modulo `libraauth.session_auth._captcha_de`
    porque el router la resuelve por nombre en cada request: parchear
    `app.state.captcha` no alcanzaria a los tests que arman su propia app.
    """
    monkeypatch.setattr("libraauth.session_auth._captcha_de", lambda request: _CAPTCHA_DE_PRUEBA)


# ── Ningun test sale a la red de verdad ─────────────────────────────────────
#
# 🔴 Lo pone un caso real del 2026-08-23. `app/mp_api.py` es un shim
# (`from libracore.mp_api import ...`), asi que `app.mp_api.obtener_pago` es un
# binding DISTINTO del que resuelve el codigo del motor. Cuando el webhook se
# mudo a `libracore.mp_webhook`, tres tests que hacian
# `monkeypatch.setattr(mp_api, "obtener_pago", ...)` dejaron de interceptar
# nada y **salieron a la API real de MercadoPago**: 401, y el caso se leyo como
# "no facturo".
#
# El problema no es el 401 -- es que un test pueda pegarle a un servicio
# externo sin que nadie se entere. En un runner con credenciales validas
# hubiera pasado en verde consultando pagos ajenos.
#
# Con esto, un parcheo que erra el modulo falla diciendo QUE se intento llamar.

_HOSTS_PROHIBIDOS = ("api.mercadopago.com", "afip.gov.ar", "arca.gob.ar")


@pytest.fixture(autouse=True)
def sin_red_de_verdad(monkeypatch, request):
    """Corta cualquier salida a un servicio externo desde la suite.

    Se puede levantar en un test puntual con `@pytest.mark.con_red`, para el
    dia que haga falta un test de integracion de verdad.
    """
    if request.node.get_closest_marker("con_red"):
        return

    import httpx

    real = httpx.AsyncHTTPTransport.handle_async_request
    real_sync = httpx.HTTPTransport.handle_request

    def _revisar(request_):
        host = request_.url.host or ""
        if any(host.endswith(p) or host == p for p in _HOSTS_PROHIBIDOS):
            raise RuntimeError(
                f"Un test intento salir a {host} ({request_.url}). "
                "Casi seguro un monkeypatch que erro el modulo: si la funcion "
                "vive en libracore, hay que parchear `libracore.<modulo>`, no "
                "el shim de `app/`."
            )

    async def _async(self, request_, **kw):
        _revisar(request_)
        return await real(self, request_, **kw)

    def _sync(self, request_, **kw):
        _revisar(request_)
        return real_sync(self, request_, **kw)

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", _async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _sync)
