"""Auth para la API JSON de la SPA (ver wiki/entities/contalibra.md,
migracion a React). Reusa la mecanica de cookie de web/auth.py (SessionAuth
sobre `cl_session`) tal cual -- ya es correcta para un cliente JSON, misma
cookie same-origin. Lo que no se reusa es require_auth/require_role: esos
devuelven un redirect 307 a /login, que tiene sentido para las rutas HTML
pero rompe un fetch/axios (el caller recibe el HTML de login.html donde
esperaba JSON). Estas dependencias devuelven 401/403 en su lugar. Ambas
conviven sobre la misma cookie hasta que las rutas HTML se borren en la
etapa de corte de la migracion. Mismo patron que gestiolibra/app/auth.py.
"""
import hmac
import os

from fastapi import Depends, HTTPException, Request
from libraauth.session_auth import (
    SERVICE_USER,
    permite_lectura_de_demo,
    token_de_servicio_valido,
)

from app import database as db
from app.web.auth import get_current_user as _get_username_from_cookie

#: Credencial del panel del dueño, **distinta del token de servicio**.
#
# 🔴 `LIBRA_SERVICE_TOKEN` es **por producto, no por instancia**: medido el
# 2026-08-20, `contalibra` y `contalibra-demo` comparten uno, y
# `libradesk-lagrace` y `libradesk-compulibra` —dos clientes distintos— también.
# Dárselo al panel de un cliente le abriría las instancias de los demás,
# empezando por la de la propia empresa del proveedor.
#
# Por eso el panel lleva su propia credencial, propia de cada instancia, y su
# propio header: una filtrada expone la lectura de agregados de **una** sucursal
# y de nada más, y no se puede repetir como token de servicio.
# Ver wiki/analyses/panel-del-dueno-multisucursal.md.
PANEL_TOKEN_ENV = "LIBRA_PANEL_TOKEN"
PANEL_TOKEN_HEADER = "x-panel-auth"

PANEL_USER = {
    "id": None,
    "username": "panel",
    "nombre": "Panel del dueño",
    "role": "admin",
}


def token_de_panel_valido(request: Request) -> bool:
    """Igual que `token_de_servicio_valido`, con otra variable y otro header.

    **Opt-in por ausencia**: sin la variable en el entorno devuelve False sin
    mirar el header, así que una instancia que no participa del panel no expone
    nada de más.
    """
    esperado = os.environ.get(PANEL_TOKEN_ENV, "")
    if not esperado:
        return False
    recibido = request.headers.get(PANEL_TOKEN_HEADER, "")
    # `compare_digest` y no `==`, por el mismo motivo que en libraauth: comparar
    # con el operador normal filtra el largo y el prefijo por el tiempo.
    return bool(recibido) and hmac.compare_digest(recibido, esperado)


def get_current_user_json(request: Request) -> dict:
    username = _get_username_from_cookie(request)
    if not username:
        raise HTTPException(401, "No autenticado")
    user = db.get_usuario_by_username(username)
    if not user:
        raise HTTPException(401, "No autenticado")
    return user


def require_role_json(*roles: str):
    """Factory de dependencia: 403 si el usuario logueado no tiene uno de roles.

    **Excepcion: el visitante de la demo publica pasa, pero solo para leer.**
    La regla no se escribe aca: sale de `libraauth.permite_lectura_de_demo`,
    la misma que usan los otros cuatro productos. Si se duplicara, cambiar que
    puede ver un visitante seria tocar dos lugares — y el que se olvide queda
    distinto sin que nadie lo note.
    """

    def _dep(request: Request, user: dict = Depends(get_current_user_json)) -> dict:
        if user["role"] in roles:
            return user
        if permite_lectura_de_demo(request, user):
            return user
        raise HTTPException(403, "No autorizado")

    return _dep


require_admin_json = require_role_json("admin")


def require_admin_o_servicio_json(request: Request) -> dict:
    """Rol admin **o** token de servicio (libraauth v0.7.0).

    Lo necesita el backoffice compartido de la suite
    (`admin.contalibra.com.ar`), que administra las instancias y **no es
    usuario de ninguna**: no tiene fila en la tabla `usuarios` de ningún
    cliente, así que `require_admin_json` lo rechaza siempre.

    El token se chequea antes que la sesión a propósito: una request del
    backoffice no trae cookie, así que evaluar la sesión primero daría 401 y no
    se llegaría a mirar el header nunca.

    **Opt-in por ausencia**: sin `LIBRA_SERVICE_TOKEN` en el entorno,
    `token_de_servicio_valido` devuelve False sin mirar el header y esto se
    comporta igual que `require_admin_json`.
    """
    if token_de_servicio_valido(request):
        return dict(SERVICE_USER)
    usuario = get_current_user_json(request)
    if usuario["role"] == "admin":
        return usuario
    # Misma excepción de lectura, y hace falta acá aparte: éste no pasa por
    # `require_role_json`, y de él cuelga la pantalla de Usuarios.
    if permite_lectura_de_demo(request, usuario):
        return usuario
    raise HTTPException(403, "No autorizado")


def require_panel_o_admin_json(request: Request) -> dict:
    """Credencial del panel del dueño **o** un admin de esta instancia.

    El admin sirve para que la pantalla del propio producto pueda consumir el
    mismo endpoint sin una segunda implementación, y para poder probarlo con una
    sesión normal.

    **No acepta el token de servicio a propósito.** Ese es del backoffice de
    superadmin y es compartido entre las instancias de un producto; mezclarlos
    haría que la credencial del panel de un cliente valiera para las instancias
    de otro — ver el comentario de `PANEL_TOKEN_ENV`.
    """
    if token_de_panel_valido(request):
        return dict(PANEL_USER)
    usuario = get_current_user_json(request)
    if usuario["role"] == "admin":
        return usuario
    raise HTTPException(403, "No autorizado")
