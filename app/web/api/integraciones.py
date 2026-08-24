"""Consultas que llegan desde otro producto de la familia, para facturar acá.

Lo estrena [[medlibra]]: el consultorio completa un turno y lo manda a Contalibra,
que es donde vive la contabilidad. El endpoint no sabe de salud — recibe *"esto
se hizo, salió tanto, se cobró así"*.

## 🔴 Quién es el dueño de la venta lo decide ESTA instancia

El pedido **no trae** a qué usuario atribuir la venta, y es a propósito: si
viniera en el payload, cualquiera con el token de servicio podría atribuirle
ventas a cualquier usuario. La instancia configura una vez su
`usuario_integraciones` y todo lo externo se atribuye a él.

Y sin ese usuario configurado el endpoint **rechaza** en vez de crear la venta
sin dueño. Una venta sin `usuario_id` entra igual, suma su movimiento de caja y
queda **fuera de todo turno**: el cierre de caja no la ve. Fallar cerrado es lo
único que evita que ese descuadre se descubra a fin de mes.

## Idempotencia

`(sistema, referencia)` es único. Un reintento del emisor —un timeout, un deploy
en el medio— devuelve **la misma venta**, no una segunda con su segunda factura.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import database as db
from app import venta_facturacion
from app.web.api_auth import require_admin_json, require_admin_o_servicio_json

router = APIRouter(prefix="/api/integraciones", tags=["integraciones"])


class PacientePayload(BaseModel):
    """Quién recibió la prestación.

    Los datos fiscales son opcionales y deciden el **tipo de comprobante**: con
    CUIT y condición se busca (o se crea) el cliente y la factura sale A o B
    según corresponda; sin ellos va como Consumidor Final, que es el caso
    normal de un consultorio.
    """

    nombre: str
    cuit: str = ""
    condicion_iva: str = ""


class ConsultaPayload(BaseModel):
    #: Qué producto manda. Junto con `referencia` forma la clave de idempotencia.
    sistema: str = Field(min_length=1)
    #: El identificador de la consulta EN EL PRODUCTO EMISOR (el id del turno).
    #: Es lo que hace que un reintento no facture dos veces.
    referencia: str = Field(min_length=1)
    fecha: str
    descripcion: str = Field(min_length=1)
    importe: float = Field(gt=0)
    medio_pago: str = Field(min_length=1)
    paciente: PacientePayload
    #: La alícuota de la prestación, si el emisor la sabe. `None` manda el
    #: default de esta instancia. En salud el caso normal es el **exento**, y
    #: esa configuración es del producto que presta, no del que factura.
    #:
    #: 🔴 **Es una fracción, no un porcentaje**, y por eso el `le=1`: mandar
    #: `21` queriendo decir 21% facturaría al **2100%**, y ni el emisor ni esta
    #: casa tienen forma de notarlo — el total lo pone la venta, así que el
    #: comprobante sale con un neto absurdo y un CAE real encima. Rebotar con
    #: 422 es lo único que lo detiene a tiempo.
    iva_rate: float | None = Field(default=None, ge=0, le=1)
    #: Si además de registrar la venta hay que emitir la factura. En `false`
    #: queda como venta cobrada sin comprobante, para facturarla desde acá.
    facturar: bool = True


class UsuarioIntegracionesPayload(BaseModel):
    #: `""` desconfigura y **apaga** la integración: el endpoint pasa a rechazar.
    username: str = ""


@router.get("/config", dependencies=[Depends(require_admin_json)])
def ver_config():
    """Qué usuario recibe las ventas externas. Sólo admin de la instancia:
    **no** acepta el token de servicio, que es justamente lo que la usa."""
    return {"usuario_integraciones": db.get_usuario_integraciones()}


@router.put("/config", dependencies=[Depends(require_admin_json)])
def fijar_config(payload: UsuarioIntegracionesPayload):
    username = payload.username.strip()
    if username and not db.get_usuario_by_username(username):
        raise HTTPException(422, f"No existe el usuario «{username}» en esta instancia.")
    db.set_usuario_integraciones(username)
    return {"usuario_integraciones": db.get_usuario_integraciones()}


def _usuario_de_integraciones() -> dict:
    """El usuario al que se atribuyen las ventas externas. Falla cerrado."""
    username = db.get_usuario_integraciones()
    if not username:
        raise HTTPException(
            409,
            "Esta instancia no tiene configurado el usuario para integraciones. "
            "Configuralo en Integraciones antes de recibir consultas externas.",
        )
    usuario = db.get_usuario_by_username(username)
    if not usuario:
        # Configurado pero borrado después. Es peor que no configurado: parece
        # que está listo.
        raise HTTPException(
            409,
            f"El usuario para integraciones («{username}») ya no existe en esta "
            "instancia. Volvé a configurarlo.",
        )
    return usuario


def _cliente_para(paciente: PacientePayload) -> int | None:
    """El cliente al que va la venta, o `None` para Consumidor Final.

    Se busca **por CUIT** y se crea si no está. Buscar por nombre haría que dos
    personas homónimas compartan cuenta corriente y comprobantes; el CUIT es lo
    único que identifica a un contribuyente.
    """
    cuit = paciente.cuit.strip()
    if not cuit:
        return None
    existente = db.get_client_by_cuit(cuit)
    if existente:
        return existente["id"]
    return db.create_client(
        name=paciente.nombre.strip(),
        cuit_dni=cuit,
        iva_condition=paciente.condicion_iva.strip() or "Consumidor Final",
    )


@router.post("/consultas", dependencies=[Depends(require_admin_o_servicio_json)])
async def registrar_consulta(payload: ConsultaPayload):
    """Registra la consulta como venta cobrada y —si se pide— la factura.

    Devuelve `{"venta": ..., "factura": ..., "ya_existia": bool}`.
    """
    usuario = _usuario_de_integraciones()

    ya = db.get_venta_por_referencia(payload.sistema, payload.referencia)
    if ya is not None:
        # 🔴 El reintento NO vuelve a facturar: `facturar_venta` es idempotente
        # (si la venta ya tiene factura devuelve ésa), así que pedirlo de nuevo
        # es seguro y además cubre el caso de que el intento anterior haya
        # creado la venta y fallado al pedir el CAE.
        venta = db.get_venta(ya)
        factura = None
        if payload.facturar and not venta.get("factura_id"):
            factura = await _facturar(ya, usuario["id"])
        elif venta.get("factura_id"):
            factura = db.get_factura(venta["factura_id"])
        return {"venta": db.get_venta(ya), "factura": factura, "ya_existia": True}

    cliente_id = _cliente_para(payload.paciente)
    items = [{
        "nombre": payload.descripcion.strip(), "qty": 1.0,
        "precio": payload.importe, "subtotal": payload.importe,
        "producto_id": None,
    }]
    mods = db.get_modulos()
    venta_id = db.crear_venta_directa(
        fecha=payload.fecha,
        items=items,
        subtotal=payload.importe,
        descuento=0.0,
        total=payload.importe,
        cliente_id=cliente_id,
        cliente_nombre=payload.paciente.nombre.strip(),
        usuario_id=usuario["id"],
        observaciones=f"{payload.sistema} · {payload.referencia}",
        estado="cobrada",
        pagos=[{"medio": payload.medio_pago, "monto": payload.importe, "referencia": ""}],
        stock_habilitado=bool(mods.get("stock")),
    )
    # Fuera de la transacción de la venta: `crear_venta_directa` la abre y la
    # cierra sola, y no expone su `conn`. La ventana es chica pero existe — si
    # el proceso muriera justo acá, un reintento crearía una segunda venta. Se
    # asume: partir esa función para pasarle la referencia sería tocar el camino
    # del mostrador, que es el que usan todos los días.
    db.registrar_origen(
        venta_id, payload.sistema, payload.referencia, payload.iva_rate,
    )

    factura = await _facturar(venta_id, usuario["id"]) if payload.facturar else None
    return {"venta": db.get_venta(venta_id), "factura": factura, "ya_existia": False}


async def _facturar(venta_id: int, usuario_id: int):
    """Emite la factura, o `None` si el módulo de facturación está apagado.

    No se rechaza el pedido por eso: la venta **ya está registrada y cobrada**,
    que es la mitad que siempre corresponde. Devolver 4xx dejaría al emisor
    reintentando —y por la idempotencia, sin crear nada— para siempre.
    """
    if not db.get_modulos().get("facturacion"):
        return None
    try:
        return await venta_facturacion.facturar_venta(venta_id, usuario_id=usuario_id)
    except venta_facturacion.VentaNoFacturable as e:
        raise HTTPException(422, str(e))
