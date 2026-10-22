"""La costura de Contalibra con LibraEdge: lo único del nodo offline que es de este producto (E6, 2026-10-19).

El nodo offline es la instancia de Contalibra que corre en la PC del local y sigue **vendiendo y cobrando en el
mostrador** sin internet. Es genérico de la suite: el aprovisionamiento del central es de LibraEdge (ADR-008,
`libraedge-central nodo ...`), las ventas suben por la capa ERP de LibraCommerce (ADR-067 y ADR-068,
`libracommerce.erp.offline`) y la facturación del nodo es de LibraCore (ADR-074, `libracore.nodo_offline`). RestoLibra
fue el primer adoptante (E5); lo que queda acá es declarativo.

| Pieza | Qué aporta este producto |
|---|---|
| `aprovisionamiento` | las tablas de referencia (el reparto de autoridad) y las sucursales |
| `OUTBOX` | la identidad del nodo y si está en línea. Sin `extra_de_venta`: la venta de mostrador no lleva nada propio |
| `GANCHOS_DE_CAJA` | la caja del nodo (turnos y movimientos a mano) sube al central como operaciones |
| `altas_en_nodo` | los clientes que se dan de alta en el nodo (id provisorio y `cliente.alta`) suben al central |
| `offline_stock` | el stock de la sucursal del nodo: sus ajustes suben (`stock.movimiento`), el central se niega a moverlo (409) y la carga inicial lo trae al vincular |
| `CONEXION` / `numerar_en_el_nodo` | en el nodo, facturar con el ticket de ARCA que presta el central |

🔑 **Fuera de un nodo nada cambia.** Una instancia común —Compulibra, la demo— no tiene `LIBRAEDGE_NODE_ID`:
`nodo()` es `None`, el outbox no encola, el numerador no lleva prefijo, la facturación numera como siempre y la
bandeja no recibe ventas. Lo sostienen `tests/test_libraedge_fuera_de_un_nodo.py`.

## Identidad: `LIBRAEDGE_NODE_ID` (y `CONTALIBRA_EDGE_NODE_ID`)

`nodo()` es `libraedge.identidad.nodo_actual("CONTALIBRA")`: lee la variable general y la del producto; si están las
dos y difieren, `IdentidadEnConflicto`. Es la **identidad** del nodo (la escribe el instalador). **LibraEdge está
incluido en todos los planes** (decisión del humano, 2026-10-20; libraedge ADR-014): no hay adicional `offline` ni
guarda comercial al registrar un nodo (`sin_guarda`).

El prefijo de numeración (`LIBRAEDGE_PREFIJO`, `S02`) lo asigna el central al registrar el nodo. **Un nodo sin prefijo
no vende**: `NodoLocal` levanta `ValueError` en la primera venta, porque numeraría igual que el central.

## Qué hace el nodo, y qué no (fase 1)

Vende y cobra en el mostrador, anula y devuelve; todo sube al central como
operaciones (`venta.registrada`, `venta.pago_acreditado`, `venta.anulada`, `venta.devolucion`, `venta.facturada`).
También **abre y cierra turnos, anota y anula movimientos de caja a mano** y todo eso sube (`turno.abierto`,
`turno.cerrado`, `caja.movimiento`, `caja.movimiento_anulado`; decisión del humano, 2026-10-21; libracore ADR-076 y
libracommerce ADR-069): los routers de caja y de turnos reciben `GANCHOS_DE_CAJA`. Los movimientos que nacen de una venta
**no** se enganchan: los reproduce el central al aplicar la venta. Este producto no monta el cierre diario
(`build_cierre_diario_router`): no hay `dia.cerrado` que subir ni `reabrir` que proteger.
**Mueve el stock de su sucursal** (decisión del humano, 2026-10-21; libracommerce ADR-071): los ajustes —también el de modo
entrada, que es como entra la mercadería: Contalibra no tiene compras ni recepciones— y las transferencias entre sus
depósitos suben como `stock.movimiento`. Al vincular trae las existencias de su sucursal del central (libraedge ADR-023) y
desde ahí manda el nodo: **el central contesta 409 a todo movimiento de stock sobre los depósitos de una sucursal con nodo**
(ajustes, transferencias y ventas desde la web). Un depósito sin sucursal no es de ningún nodo, así que no se vincula
mientras haya uno.
Factura **desde la venta** con internet (ticket prestado) y, sin conexión, la venta queda en la bandeja y se factura
sola al volver. **No** emite facturas sueltas, remitos, presupuestos, recibos ni notas: eso es del central y necesita
internet. Sin conexión el QR de MercadoPago está apagado.

## Aprovisionar (en el central)

    LIBRAEDGE_APROVISIONAMIENTO=app.offline:aprovisionamiento libraedge-central nodo publicar
    libraedge-central nodo sucursales | registrar <node_id> --sucursal <id o nombre> | estado | dar-de-baja <id>
    libraedge-central nodo vigilar --umbral 15
    LIBRAEDGE_DESPACHADOR=app.web.routers.sincronizacion_offline:despachador libraedge-central revision listar ...

Ver «Nodo offline (LibraEdge)» en `OPERACIONES.md`.
"""

from __future__ import annotations

import os

from libracommerce.erp import offline_stock
from libracommerce.erp.offline import NodoLocal, Outbox
from libracommerce.erp.offline_caja import caja_con_outbox
from libracommerce.erp.offline_clientes import altas_en_nodo as altas_de_clientes
from libracore import altas_en_nodo
from libracore.altas_en_nodo import REFERENCIAS_DE_CLIENTES
from libracore.ganchos_de_caja import GanchosDeCaja
from libracore.nodo_offline import VARIABLE_ESTADO, ConexionDelNodo, esta_en_linea
from libraedge.identidad import nodo_actual, prefijo_actual

#: El prefijo de las variables del producto (`CONTALIBRA_DATABASE_URL`, `CONTALIBRA_EDGE_NODE_ID`).
PREFIJO = "CONTALIBRA"

#: El `origen_producto` de la bandeja de comprobantes pendientes y del candado por venta (libracore ADR-074).
PRODUCTO = "contalibra"

#: El reparto de autoridad: qué tablas manda el central y el nodo sólo espeja. **Sólo los nombres**: la clave la lee
#: LibraEdge de la base (escribirla a mano se equivocó en silencio en el piloto: `units` tiene PK `code`, no `id`).
#: Lo que el mostrador del nodo necesita para vender, cobrar y facturar, y nada más:
#:
#: - **Quién entra y qué ve:** `usuarios` (el cajero se loguea en el nodo) y `modulos` (los mismos módulos que el
#:   central; el adicional `offline` incluido).
#: - **Qué se vende y a cuánto:** el catálogo de LibraCommerce (`catalog_items`, `item_variants`, `item_codes` —el
#:   código de barras—, `categories`, `units`), los precios (`price_lists`, `item_prices`) y `commerce_settings` (el
#:   formato de la balanza). `cliente_lista_precio` es el adicional mayorista: la lista de precios de cada cliente.
#: - **A quién:** `clients` y su espejo comercial `parties` (el fiado y la factura A necesitan al cliente con su CUIT).
#: - **Dónde:** `branches` (la sucursal del nodo; Contalibra tiene la sucursal única «Casa central», F1) y `locations`
#:   (los depósitos de los que sale el stock).
#: - **Con qué caja:** `cajas` (y con ella sus medios de pago, que viven en la propia fila: no hay tabla aparte) y
#:   `cuentas_tesoreria`. El punto de venta de la factura se resuelve por la caja del turno.
#: - **Facturar con internet:** `arca_config` (CUIT, punto de venta, ambiente; las rutas del certificado no se usan en
#:   el nodo, que firma con el ticket que presta el central: la clave no sale del VPS).
#: - `proveedores`: lo referencia el catálogo (el proveedor del producto).
#:
#: Ninguna tiene una FK hacia una tabla que no esté acá (lo verifica `tests/test_libraedge_de_punta_a_punta.py`).
#:
#: 🔴 NO están `productos`, `categorias_producto`, `listas_precio`, `lista_precio_items` ni `depositos`: las crea el DDL
#: de LibraCore, pero desde P7 el catálogo, los precios y los depósitos de este producto viven en las tablas de
#: LibraCommerce. Tampoco `arca_credenciales_servicio` ni lo de MercadoPago (`mp_*`, `facturacion_alias`): sin conexión
#: el QR está apagado (libracore ADR-074) y las credenciales no salen del central.
#:
#: Las de **autoridad del nodo** (`sales` y lo suyo, `caja_movimientos`, `turnos_caja`, `stock_movements`, `facturas`,
#: `venta_links`, la bandeja de comprobantes y el libro de clientes) no se publican: el nodo las genera y las sube como
#: operaciones. Las de **sólo el central** (remitos, presupuestos, recibos, egresos, tesorería, compras, la ingesta por
#: integración: `integraciones_config`, `ventas_origen_externo`) tampoco: el nodo no las usa.
TABLAS_DE_REFERENCIA = frozenset({
    # LibraCore
    "usuarios", "modulos", "clients", "proveedores", "cuentas_tesoreria", "cajas", "arca_config",
    # LibraCommerce
    "catalog_items", "item_variants", "item_codes", "categories", "units", "price_lists", "item_prices",
    "commerce_settings", "parties", "branches", "locations", "cliente_lista_precio",
})


# ── La identidad y la conexión del nodo ─────────────────────────────────────────────────────────────────────────────


def nodo() -> str | None:
    """El id de este nodo, o `None` si la instancia no es un nodo offline (el central, o una instalación común).

    Se lee en cada llamada: activar el nodo no exige reiniciar nada y la suite no depende del orden de los tests."""
    return nodo_actual(PREFIJO)


def nodo_local() -> NodoLocal | None:
    """La identidad de este nodo con su prefijo de numeración, para el outbox de LibraCommerce."""
    node_id = nodo()
    if node_id is None:
        return None
    return NodoLocal(node_id=node_id, prefijo=prefijo_actual() or "")


def en_linea() -> bool:
    """Si el nodo ve al central: lo que dice el archivo de estado del proceso del nodo (`LIBRAEDGE_ESTADO`).

    Es la de libracore (ADR-074): el último ciclo sincronizó y la última sincronización buena es reciente. Sin archivo,
    viejo o ilegible, sin conexión. La ruta se lee en cada llamada (`conexion_desde_entorno` la congela al armarse)."""
    return esta_en_linea((os.environ.get(VARIABLE_ESTADO) or "").strip() or None)


#: Lo que LibraCore pregunta antes de salir a ARCA o a MercadoPago (va en el `PuertoDeVentas`). Fuera de un nodo,
#: nada cambia.
CONEXION = ConexionDelNodo(nodo=nodo, en_linea=en_linea)

#: El outbox de LibraEdge para `libracommerce.erp.offline.con_outbox`. El mismo en el nodo y en el central: fuera de un
#: nodo (`nodo_local()` es `None`) no encola nada. La venta de mostrador no lleva nada propio (`extra_de_venta`).
OUTBOX = Outbox(nodo=nodo_local, en_linea=en_linea)

#: Los ganchos de la caja para `build_caja_router` y `build_turnos_router` (`ganchos_de_caja=`): en un nodo encolan en el
#: `OUTBOX` el turno que se abre o se cierra y el movimiento que se anota o se anula; **fuera de un nodo** (`nodo_local()`
#: es `None`) no hacen nada, como `GanchosDeCaja()`. Se pasan por llamada y no se registran globalmente: la caja de una
#: venta no sube acá sino con la venta (`erp.offline_caja`, «Qué sube y qué no»). `OUTBOX` va con `caja_con_turno=False`
#: (el default) porque `registrar_venta` y `acreditar_pago_qr` de este producto no escriben el turno en la caja.
GANCHOS_DE_CAJA = caja_con_outbox(GanchosDeCaja(), OUTBOX)

#: Las altas de clientes en un nodo (libracore ADR-077, libracommerce ADR-070): en un nodo, cualquier alta de
#: `libracore.db.clients` (`POST /api/clientes`, el alta del cobro, el fiado, la ingesta por integración) guarda al
#: cliente con un **id provisorio negativo** y encola `cliente.alta` en el `OUTBOX`, en la misma transacción del alta; el
#: central le asigna su id y la venta a ese cliente sube traducida (`venta.registrada`). Se registra al importar este
#: módulo, que importan la app y el CLI del central (`LIBRAEDGE_APROVISIONAMIENTO`): en las dos puntas. **Fuera de un nodo**
#: (`nodo_local()` es `None`) el motor no pide ids provisorios ni avisa a nadie, y el alta es la de siempre (Compulibra).
altas_en_nodo.configurar(altas_de_clientes(OUTBOX))

#: El stock de la sucursal del nodo (libracommerce ADR-071). Una sola llamada, en las dos puntas: en un nodo cada movimiento
#: del ledger que no es de una venta encola `stock.movimiento` (en la misma transacción); en el central, la guarda le niega
#: a la web mover un depósito de una sucursal con nodo activo (`DepositoDeSucursalConNodo`, que `app/web/app.py` convierte
#: en 409). Se registra al importar este módulo, como `altas_en_nodo`. Contalibra no tiene compras: no hay
#: `recepcion_con_outbox` que enchufar. **Fuera de un nodo y sin nodos registrados** (Compulibra, la demo) no hace nada.
offline_stock.configurar(OUTBOX)


# ── Facturar en el nodo con el ticket prestado ──────────────────────────────────────────────────────────────────────

_cliente_de_ticket = None


def _version_esquema_del_nodo() -> str | None:
    """La misma versión de esquema que manda el proceso del nodo (`LIBRAEDGE_VERSION_ESQUEMA`, `alembic` por defecto),
    para que el central conteste 409 si no coinciden."""
    from libraedge.cli import version_esquema_del_nodo

    from app.db_core import get_connection

    with get_connection() as conn:
        return version_esquema_del_nodo(conn, os.environ.get("LIBRAEDGE_VERSION_ESQUEMA"))


def cliente_de_ticket():
    """El `ClienteDeTicket` de LibraEdge de este nodo (uno por proceso: guarda el ticket en memoria hasta que vence).
    Lo arma recién al primer uso: fuera de un nodo no hay a quién pedirle y `cliente_desde_entorno` levantaría."""
    global _cliente_de_ticket
    if _cliente_de_ticket is None:
        from libraedge.sync.ticket import cliente_desde_entorno

        version: list[str | None] = []

        def version_esquema() -> str | None:
            if not version:
                version.append(_version_esquema_del_nodo())
            return version[0]

        _cliente_de_ticket = cliente_desde_entorno(version_esquema=version_esquema)
    return _cliente_de_ticket


def obtener_ta_del_central():
    """El `obtener_ta(arca)` de `libracore.nodo_offline.numerador_con_ta`, sobre el transporte de LibraEdge.

    Un corte (sin red, 5xx, esquema distinto) llega como `SinConexion` y la venta va a la bandeja. Un **rechazo** del
    central (`TicketRechazado`: nodo revocado, sin ARCA, sin la ruta) se traduce a `RechazoDelCentral`: 422
    `nodo_sin_arca`, no va a la bandeja (no se arregla solo al volver la conexión)."""
    from libracore.nodo_offline import RechazoDelCentral, SinConexion
    from libraedge.sync.ticket import TicketRechazado

    base = cliente_de_ticket().para_numerador(sin_conexion=SinConexion)

    async def obtener_ta(arca: dict) -> dict:
        try:
            return await base(arca)
        except TicketRechazado as e:
            raise RechazoDelCentral(
                "El central no presta el ticket de ARCA a este equipo (nodo revocado o sin credencial).") from e

    return obtener_ta


async def numerar_en_el_nodo(punto_venta: int, tipo: int) -> tuple:
    """El `numerar_comprobante` de un nodo: el número de ARCA pedido con el ticket que presta el central. Nunca numera
    local (ese número chocaría con el de ARCA y con el del central)."""
    from libracore.nodo_offline import numerador_con_ta

    return await numerador_con_ta(obtener_ta_del_central())(punto_venta, tipo)


# ── El aprovisionamiento del central ────────────────────────────────────────────────────────────────────────────────


def sucursales_con_nodo() -> int:
    """Cuántas sucursales distintas tienen un nodo activo, con su propia conexión (hasta ADR-014 la medía el router de
    adicionales; LibraEdge ya no es un adicional, queda para quien la consulte)."""
    from libraedge.aprovisionamiento import sucursales_con_nodo as contar

    from app.db_core import get_connection

    with get_connection() as conn:
        return contar(conn)


def nodos_del_central() -> list[dict]:
    """Los nodos registrados en esta instancia, para la barra de estado del pie (libracore ADR-075): la misma lista que
    «Sucursal sin internet» (`libraedge.pantalla_del_central.nodos_de_la_instancia`, sin el hash del secreto). El motor
    usa sólo `activo` y `estado`."""
    from libraedge.pantalla_del_central import nodos_de_la_instancia

    from app.db_core import get_connection

    with get_connection() as conn:
        return nodos_de_la_instancia(conn, [])


def _listar_sucursales(conn) -> list[dict]:
    from libracommerce.erp.catalogo import get_all_sucursales

    return get_all_sucursales(conn)


def _conectar():
    from app.db_core import get_connection

    return get_connection()


def _aprovisionamiento():
    from libraedge.aprovisionamiento import Aprovisionamiento, sin_guarda

    return Aprovisionamiento(
        prefijo=PREFIJO, tablas_de_referencia=TABLAS_DE_REFERENCIA, listar_sucursales=_listar_sucursales,
        # Sin guarda comercial: LibraEdge está incluido en todos los planes (libraedge ADR-014).
        verificar_alta=sin_guarda, conectar=_conectar,
        # Los clientes se dan de alta en el nodo (id provisorio): `clients` con lo que lo referencia sin FK
        # (`cc_asientos.tercero_id`) y su `parties` espejo, a lo que apuntan las ventas.
        altas_en_nodo=[("clients", REFERENCIAS_DE_CLIENTES), "parties"],
        # Un depósito activo sin sucursal no es de ningún nodo: la guarda del central no lo ve y la carga inicial no lo trae.
        # El registro se niega hasta que tenga una (libracommerce ADR-071, libraedge ADR-023).
        validar_registro=offline_stock.depositos_sin_sucursal,
    )


#: Lo que el central necesita para aprovisionar los nodos de este producto (`LIBRAEDGE_APROVISIONAMIENTO`).
aprovisionamiento = _aprovisionamiento()
