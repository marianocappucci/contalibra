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

## 🔴 Una consulta puede tener MÁS DE UN pago

Hasta el 2026-08-24 el pedido traía **un solo `medio_pago`** y la venta se creaba
con un único pago por el importe entero. Para el mostrador alcanza; para un turno
señado, no: MedLibra cobra la seña cuando se reserva y el saldo cuando se
atiende, y pueden ser medios distintos.

Con 400 de seña por MercadoPago y 600 en efectivo, lo que entraba acá eran **1000
en efectivo**. La venta cerraba por el total correcto —la plata estaba bien
contada— y **el reparto de la caja estaba mal**. Un cierre que dice que entraron
1000 en efectivo cuando entraron 600 no cuadra contra el arqueo, y la diferencia
no tiene de dónde salir.

`pagos` es la lista. `medio_pago` sigue aceptándose para no romper a un emisor
que todavía no se actualizó, pero **son excluyentes**: mandar los dos es un
pedido ambiguo y se rechaza en vez de elegir uno.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from libracore import medios_pago

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


class PagoConsultaPayload(BaseModel):
    """Un cobro de la consulta. Una seña y un saldo son dos de éstos."""

    #: 🔴 Se valida contra el vocabulario de la familia y **falla cerrado**.
    #: Hasta hoy acá entraba cualquier string: `PagoPayload.medio` del mostrador
    #: es `str` pelado y `add_venta_pago()` tampoco mira. Un medio inventado
    #: creaba su movimiento de caja y salía en el cierre como un bucket suelto
    #: con el nombre crudo — la plata bien contada y el reparto mal. Es
    #: exactamente cómo MedLibra venía mandando `tarjeta`, que no existía en
    #: ninguna lista de esta casa.
    medio: str = Field(min_length=1)
    monto: float = Field(gt=0)
    referencia: str = ""


class ConsultaPayload(BaseModel):
    #: Qué producto manda. Junto con `referencia` forma la clave de idempotencia.
    sistema: str = Field(min_length=1)
    #: El identificador de la consulta EN EL PRODUCTO EMISOR (el id del turno).
    #: Es lo que hace que un reintento no facture dos veces.
    referencia: str = Field(min_length=1)
    fecha: str
    descripcion: str = Field(min_length=1)
    importe: float = Field(gt=0)
    #: La forma vieja: **un solo** pago por el importe entero. Se sigue
    #: aceptando para no romper a un emisor que no se actualizó todavía.
    medio_pago: str = ""
    #: La forma nueva: los pagos reales de la consulta. Una seña cobrada por
    #: MercadoPago y un saldo en efectivo son dos entradas.
    pagos: list[PagoConsultaPayload] = Field(default_factory=list)
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

    @model_validator(mode="after")
    def _validar_los_pagos(self):
        """Los pagos, en cualquiera de las dos formas, tienen que cerrar.

        🔴 **Falla cerrado, y por una razón concreta**: este endpoint marca la
        venta `cobrada` sin mirar lo pagado (a diferencia de `POST /api/ventas`,
        que deriva el estado). Con pagos que no suman el importe, eso sería una
        venta que dice estar cobrada y no lo está — y el descuadre aparece a fin
        de mes, sin nada que lo explique.
        """
        if self.pagos and self.medio_pago:
            raise ValueError(
                "Mandá `pagos` o `medio_pago`, no los dos: con ambos el pedido "
                "es ambiguo y elegir uno por nuestra cuenta sería adivinar."
            )
        if not self.pagos and not self.medio_pago:
            raise ValueError("Falta el medio de pago: mandá `pagos` o `medio_pago`.")

        for pago in self.pagos:
            # `validar()` levanta `MedioDePagoInvalido`, que es un `ValueError`,
            # así que pydantic lo convierte en 422 con el mensaje adentro.
            medios_pago.validar(pago.medio)
        if self.medio_pago:
            medios_pago.validar(self.medio_pago)

        if self.pagos:
            # Al centavo. Redondear a dos decimales antes de comparar porque los
            # dos lados vienen de floats: 400.0 + 600.0 puede no dar 1000.0 exacto
            # y rechazar por eso sería rechazar un pedido correcto.
            total = round(sum(p.monto for p in self.pagos), 2)
            if total != round(self.importe, 2):
                raise ValueError(
                    f"Los pagos suman {total} y la consulta dice {self.importe}. "
                    "Una venta que se marca cobrada tiene que estar cobrada entera."
                )
        return self

    def pagos_normalizados(self) -> list[dict]:
        """Los pagos en la forma que espera `crear_venta_directa`, venga el
        pedido en la forma nueva o en la vieja."""
        if self.pagos:
            return [
                {"medio": p.medio, "monto": p.monto, "referencia": p.referencia}
                for p in self.pagos
            ]
        return [{"medio": self.medio_pago, "monto": self.importe, "referencia": ""}]


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
        pagos=payload.pagos_normalizados(),
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
