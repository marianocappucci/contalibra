"""API de Usuarios: la sirve `libraauth.usuarios.build_users_router` (ADR-018,
v0.43.0) -- el contrato unico de la familia, en vez de la copia propia que
tenia este archivo hasta el 2026-09-13 (`UsuarioCreatePayload`/
`UsuarioUpdatePayload` con alias `nombre`/`activo` para el frontend viejo,
mas el aditivo `name`/`active` para el backoffice).

**La ruta NO cambia**: sigue siendo `/api/usuarios`, la misma que ya conoce
`app/web/app.py` (donde este `router` se monta) y el backoffice.

**Cambios de contrato para quien consuma esta API directamente** (el
frontend de este producto se actualiza en el mismo cambio -- ver
`frontend/src/pages/Usuarios.tsx`):

- La forma pasa a ser SIEMPRE `{id: str, username, name, role, active, email}`
  -- ya no hay `nombre`/`activo` ni el aditivo de las dos claves a la vez.
  `id` es un string (numérico, ver `libraauth.repository.UserRepository`), no
  un `int`.
- `DELETE` responde **204 sin cuerpo** (antes `200 {"ok": true}`).
- Nueva proteccion: no se puede DESACTIVAR al unico admin activo (antes solo
  se cubria "no degradarle el rol"). Y un admin no puede desactivarse ni
  sacarse el rol de admin a si mismo (antes solo estaba cubierto "no
  borrarse a si mismo").
- `PUT /api/usuarios/me/password` (cambiar la propia contraseña sin pedir la
  actual) se elimina: la reemplaza `POST /api/change-password`, que la SPA ya
  puede usar porque `app/web/api/auth.py` monta
  `build_json_api_auth_router(prefix="/api", ...)`, que la sirve siempre. Ver
  `frontend/src/pages/MiCuenta.tsx`.

El guard sigue siendo `require_admin_o_servicio_json` -- el mismo que ya
gateaba este router en `web/app.py` -- pasado como `admin_guard`, así que el
backoffice (token de servicio) sigue entrando igual.
"""
from libraauth.usuarios import build_users_router

from app.db_usuarios import ROLES
from app.web.api_auth import require_admin_o_servicio_json

router = build_users_router(
    prefix="/api/usuarios",
    roles=ROLES,
    admin_guard=require_admin_o_servicio_json,
)
