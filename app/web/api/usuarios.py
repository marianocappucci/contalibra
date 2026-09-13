"""API JSON de Usuarios para la SPA (ver wiki/entities/contalibra.md,
migracion a React). Reusa `db_usuarios.py` (via `database.py`) tal cual --
ver web/api/clientes.py para el patron general de esta etapa. Admin-only
en su totalidad (gateado en web/app.py con require_admin_json, no con
require_module -- "usuarios" no esta en la tabla `modulos`, igual que en
la version HTML).

**Contrato doble, aditivo (2026-09-13):** este router lo llama tanto el
frontend propio (`nombre`/`activo`) como libra-backoffice, que hace de
proxy hacia acá con el contrato de libraauth (`name`/`role`/`active`, y
`email` en el componente Usuarios.tsx). Antes `UsuarioUpdatePayload` sólo
aceptaba `nombre`/`activo`, así que un PUT del backoffice con `name`/
`active` (sin `nombre`) fallaba con 422 "field required" -- guardar el
nombre desde el backoffice no hacía nada, sin verse en la pantalla porque
la instancia nunca llegaba a persistir. Las entradas aceptan ambas formas
(`AliasChoices`); las respuestas devuelven las dos a la vez, sin sacar
ninguna, para no romper al frontend propio."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app import database as db
from app.web.api_auth import get_current_user_json

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


class UsuarioCreatePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    username: str
    nombre: str = Field(validation_alias=AliasChoices("nombre", "name"))
    email: str = ""
    password: str
    # Sin alias para `role`: backoffice y frontend propio ya mandan la misma
    # clave. OJO -- el default de libra-ui/backoffice para un alta es
    # "staff", que no es un rol valido aca (ver ROLES en db_usuarios.py) y
    # sigue dando 422; es un desacople de vocabulario entre productos, no lo
    # que este cambio ataca.
    role: str = "operador"


class UsuarioUpdatePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nombre: str = Field(validation_alias=AliasChoices("nombre", "name"))
    # `None` (ausente) = no tocar el email; `""` = borrarlo. El backoffice no
    # manda `email` en absoluto (su propio modelo `UsuarioUpdate` no lo tiene),
    # así que con un default de "" cada edición desde ahí borraba el correo en
    # silencio -- `UserRepository.update()` ya distingue None de "" para esto
    # mismo, sólo faltaba no pisarlo acá arriba.
    email: str | None = None
    role: str = "operador"
    activo: bool = Field(default=True, validation_alias=AliasChoices("activo", "active"))
    new_password: str = ""


class MiPasswordPayload(BaseModel):
    new_password: str


def _sin_password(usuario: dict) -> dict:
    return {k: v for k, v in usuario.items() if k != "password_hash"}


def _con_contrato_libraauth(usuario: dict) -> dict:
    """Aditivo: además de `nombre`/`activo` (contrato viejo, lo que lee el
    frontend propio) agrega `name`/`active` (contrato de libraauth, lo que
    lee libra-ui `Usuarios.tsx` a través del backoffice) apuntando a los
    mismos valores. Ninguna clave existente se saca."""
    return {**usuario, "name": usuario["nombre"], "active": bool(usuario["activo"])}


@router.get("")
def listar():
    return [_con_contrato_libraauth(_sin_password(u)) for u in db.get_all_usuarios()]


@router.put("/me/password")
def cambiar_mi_password(payload: MiPasswordPayload, user: dict = Depends(get_current_user_json)):
    """Faltaba -- equivalente a GET/POST /mi-cuenta del router HTML viejo
    (web/routers/usuarios.py), que dejaba a un usuario logueado cambiar su
    propia contraseña sin tocar el resto de sus datos. Se perdio por completo
    en la migracion: el sidebar viejo (base.html) tenia un link "{{ nombre
    }} ({{ role }})" -> /mi-cuenta en el footer, visible para cualquier
    usuario logueado (no solo admin), pero la ruta en si estaba gateada con
    require_admin -- se preserva ese mismo gateo aca via el
    require_admin_json que ya aplica a todo este router en web/app.py, sin
    inventar una regla de autorizacion nueva. Ver auditoria de campo por
    campo, modulo Usuarios."""
    if len(payload.new_password) < 6:
        raise HTTPException(422, "La contraseña debe tener al menos 6 caracteres.")
    db.update_usuario_password(user["id"], payload.new_password)
    return _sin_password(db.get_usuario_by_id(user["id"]))


@router.post("")
def crear(payload: UsuarioCreatePayload):
    if len(payload.password) < 6:
        raise HTTPException(422, "La contraseña debe tener al menos 6 caracteres.")
    try:
        uid = db.create_usuario(
            username=payload.username.strip(), nombre=payload.nombre.strip(),
            email=payload.email.strip(), password=payload.password, role=payload.role,
        )
    except Exception as e:
        raise HTTPException(422, str(e))
    return _con_contrato_libraauth(_sin_password(db.get_usuario_by_id(uid)))


@router.put("/{uid}")
def actualizar(uid: int, payload: UsuarioUpdatePayload):
    usuario = db.get_usuario_by_id(uid)
    if not usuario:
        raise HTTPException(404, "Usuario no encontrado")
    if usuario["role"] == "admin" and payload.role != "admin":
        admins = [u for u in db.get_all_usuarios() if u["role"] == "admin"]
        if len(admins) <= 1:
            raise HTTPException(422, "No se puede cambiar el rol del único administrador.")
    db.update_usuario(
        uid, nombre=payload.nombre.strip(),
        email=(payload.email.strip() if payload.email is not None else None),
        role=payload.role, activo=1 if payload.activo else 0,
    )
    if payload.new_password:
        if len(payload.new_password) < 6:
            raise HTTPException(422, "La contraseña debe tener al menos 6 caracteres.")
        db.update_usuario_password(uid, payload.new_password)
    return _con_contrato_libraauth(_sin_password(db.get_usuario_by_id(uid)))


@router.delete("/{uid}")
def eliminar(uid: int, user: dict = Depends(get_current_user_json)):
    usuario = db.get_usuario_by_id(uid)
    if not usuario:
        raise HTTPException(404, "Usuario no encontrado")
    if usuario["username"] == user["username"]:
        raise HTTPException(422, "No podés eliminar tu propio usuario.")
    if usuario["role"] == "admin":
        admins = [u for u in db.get_all_usuarios() if u["role"] == "admin"]
        if len(admins) <= 1:
            raise HTTPException(422, "No se puede eliminar al único administrador.")
    db.delete_usuario(uid)
    return {"ok": True}
