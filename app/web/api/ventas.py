"""API JSON de Ventas (POS) para la SPA (ver wiki/entities/contalibra.md,
migracion a React). Reusa `db_ventas.py` (via `database.py`) tal cual --
ver web/api/clientes.py para el patron general de esta etapa.

El QR dinamico de MercadoPago (`POST /ventas/{id}/mp-qr`,
`GET /ventas/{id}/mp-status`), el autocompletado de productos
(`GET /productos/buscar`) y los PDFs (`GET /ventas/{id}/ticket`,
`GET /ventas/{id}/recibo`) siguen viviendo en sus routers HTML tal cual
(ya son JSON o descargas autenticadas por cookie) -- la SPA los consume
directo, sin reimplementarlos.
"""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from libracore import medios_pago
from libracore import pagos as acreditacion
from pydantic import BaseModel, field_validator, model_validator

from app import database as db
from app import venta_facturacion
from app.web.api_auth import get_current_user_json, require_role_json

router = APIRouter(prefix="/api/ventas", tags=["ventas"])

# 🔴 Del motor, no de una copia escrita acá — ver la nota en `api/cajas.py`, que
# tenía esta misma lista repetida byte a byte en el mismo repo.
MEDIOS_PAGO = medios_pago.para_selector()

#: El medio con el que cobra el QR de caja. Pasa por `medios_pago.validar` y no
#: es un literal suelto: la grafía se normalizó a `mercadopago` el 2026-08-25
#: —era la última divergencia del vocabulario de la familia— y este archivo no
#: puede volver a tener su propia versión de ese string.
MEDIO_DEL_QR = medios_pago.validar("mercadopago")


class ItemPayload(BaseModel):
    nombre: str
    qty: float
    precio: float
    producto_id: int | None = None


class PagoPayload(BaseModel):
    #: 🔴 **Se valida.** Hasta el 2026-08-24 era un `str` pelado, y
    #: `add_venta_pago()` tampoco miraba: la lista de medios sólo existía para
    #: poblar el `<Select>`. Un medio inventado entraba, creaba su movimiento de
    #: caja y salía en el cierre como un bucket suelto con el nombre crudo — la
    #: plata bien contada y **el reparto mal**. Nadie se enteraba.
    #:
    #: Las seis grafías de siempre siguen siendo válidas, así que un frontend
    #: viejo no se rompe; lo que rebota es lo que nunca debió entrar.
    medio: str
    monto: float
    referencia: str = ""
    #: 🔴 **"Este pago todavía no entró: lo voy a cobrar con el QR ahora."**
    #:
    #: Es la única forma de distinguir las dos cosas que el mostrador puede
    #: querer decir con el medio `mercadopago`: *"el cliente ya me transfirió"*
    #: —el cajero vio la plata— y *"le voy a cobrar recién ahora"*. Sin este
    #: campo las dos entran iguales, y la venta nace cobrada con su movimiento
    #: de caja escrito **antes de que nadie escanee nada**.
    #:
    #: Con esto en `true` el pago nace `PENDIENTE`: no cuenta para el estado de
    #: la venta y **no toca la caja**. Lo acredita el poll del QR o el webhook,
    #: cuando MercadoPago dice que la plata entró.
    #:
    #: Se eligió declararlo acá y no deducirlo del botón "Cobrar con QR" del
    #: detalle: por ese otro camino el ingreso **ya está escrito**, y habría que
    #: anularlo para volver atrás — dejando en el arqueo una anulación que nunca
    #: fue tal, y una ventana en la que la caja cuenta plata que no entró.
    cobrar_con_qr: bool = False

    @field_validator("medio")
    @classmethod
    def _medio_del_vocabulario(cls, v: str) -> str:
        return medios_pago.validar(v)

    @model_validator(mode="after")
    def _el_qr_es_de_mercadopago(self):
        """Un `cobrar_con_qr` sobre efectivo no significa nada.

        Rebota en vez de ignorarse: un frontend que lo mandara en el medio
        equivocado dejaría la venta pendiente **para siempre** —nada la va a
        acreditar— y el síntoma sería una venta impaga que el cajero jura haber
        cobrado.
        """
        if self.cobrar_con_qr and self.medio != MEDIO_DEL_QR:
            raise ValueError(
                f"`cobrar_con_qr` sólo aplica al medio '{MEDIO_DEL_QR}': el QR "
                f"de MercadoPago no cobra un pago en '{self.medio}'."
            )
        return self


class VentaPayload(BaseModel):
    fecha: str
    items: list[ItemPayload]
    descuento: float = 0
    cliente_id: int | None = None
    cliente_nombre: str = ""
    observaciones: str = ""
    pagos: list[PagoPayload]


@router.get("/medios-pago")
def listar_medios_pago():
    # 🔴 Se llamaba `medios_pago` y **tapaba al módulo del motor** dentro de este
    # archivo: `medios_pago.validar(...)` reventaba con "'function' object has no
    # attribute 'validar'". La ruta no cambia — el nombre de la función no es
    # parte del contrato HTTP.
    return MEDIOS_PAGO


@router.get("")
def listar(desde: str = "", hasta: str = "", q: str = "", tab: str = "todas"):
    if tab not in ("todas", "sin_facturar", "facturadas"):
        tab = "todas"
    return db.get_all_ventas(desde=desde, hasta=hasta, q=q, tab=tab)


@router.post("")
def crear(payload: VentaPayload, user: dict = Depends(get_current_user_json)):
    items = [
        {
            "nombre": i.nombre.strip(), "qty": i.qty, "precio": max(0.0, i.precio),
            "subtotal": round(i.qty * max(0.0, i.precio), 2), "producto_id": i.producto_id,
        }
        for i in payload.items if i.nombre.strip() and i.qty > 0
    ]
    if not items:
        raise HTTPException(422, "Debe agregar al menos un ítem.")

    subtotal = round(sum(i["subtotal"] for i in items), 2)
    descuento = min(max(0.0, payload.descuento), subtotal)
    total = round(subtotal - descuento, 2)

    # 🔑 **El mostrador declara si la plata entró o todavía no.**
    #
    # Sin `cobrar_con_qr` el pago es `APROBADO`: cargar un pago acá significa
    # que el cajero vio la plata — una transferencia, el efectivo, la tarjeta.
    # Con `cobrar_con_qr` el pago nace `PENDIENTE`, porque el cliente todavía
    # no escaneó nada.
    #
    # Que el estado se declare acá y no lo ponga la base es el punto: la columna
    # tiene default `'aprobado'` para poder backfillear las filas viejas, así
    # que sin esta línea un pago contaría como entrado sin que nadie lo decida.
    pagos = [
        {"medio": p.medio, "monto": p.monto, "referencia": p.referencia,
         "estado": (acreditacion.EstadoAcreditacion.PENDIENTE if p.cobrar_con_qr
                    else acreditacion.EstadoAcreditacion.APROBADO)}
        for p in payload.pagos if p.monto > 0
    ]
    if not pagos:
        raise HTTPException(422, "Debe registrar al menos un medio de pago.")
    # 🔴 Sólo lo **acreditado** decide si la venta está cobrada. Una venta que se
    # va a cobrar con el QR nace `pendiente` y sin movimiento de caja: el arqueo
    # no cuenta esa plata hasta que MercadoPago diga que entró.
    total_pagado = float(acreditacion.acreditado(pagos))

    cliente_nombre = payload.cliente_nombre.strip()
    if payload.cliente_id:
        c = db.get_client(payload.cliente_id)
        if c:
            cliente_nombre = c["name"]

    if total_pagado >= total:
        estado = "cobrada"
    elif total_pagado > 0:
        estado = "parcial"
    else:
        estado = "pendiente"

    mods = db.get_modulos()
    try:
        venta_id = db.crear_venta_directa(
            fecha=payload.fecha, items=items, subtotal=subtotal, descuento=descuento,
            total=total, cliente_id=payload.cliente_id, cliente_nombre=cliente_nombre,
            usuario_id=user["id"], observaciones=payload.observaciones.strip(), estado=estado,
            pagos=pagos, stock_habilitado=bool(mods.get("stock")),
        )
    except (sqlite3.IntegrityError, RuntimeError):
        raise HTTPException(409, "No se pudo registrar la venta (conflicto con otra venta simultánea). Reintentá.")

    return db.get_venta(venta_id)


@router.get("/{vid}")
def detalle(vid: int):
    venta = db.get_venta(vid)
    if not venta:
        raise HTTPException(404, "Venta no encontrada")
    return venta


@router.post("/{vid}/anular", dependencies=[Depends(require_role_json("admin"))])
def anular(vid: int, user: dict = Depends(get_current_user_json)):
    if not db.get_venta(vid):
        raise HTTPException(404, "Venta no encontrada")
    db.anular_venta(vid, usuario_id=user["id"])
    return db.get_venta(vid)


@router.post("/{vid}/facturar")
async def facturar(vid: int, user: dict = Depends(get_current_user_json)):
    """Emite la factura de la venta y las vincula.

    Es el mismo camino que usa el webhook de MercadoPago cuando la
    auto-facturación está activada, así que sirve también para reintentar una
    venta cuyo CAE falló. Idempotente: si ya tiene factura devuelve esa.
    """
    try:
        factura = await venta_facturacion.facturar_venta(vid, usuario_id=user["id"])
    except venta_facturacion.VentaNoFacturable as e:
        raise HTTPException(422, str(e))
    return {"venta": db.get_venta(vid), "factura": factura}
