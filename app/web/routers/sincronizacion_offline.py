"""El central expone la sincronización del nodo offline: `/sync/v1/push`, `/sync/v1/pull` y `/sync/v1/ticket-arca`.

E6 de LibraEdge (2026-10-19): Contalibra adopta el nodo genérico de la suite, con RestoLibra de modelo.

## Por qué se monta siempre, y no sólo en las instancias con nodos

El gateo está del otro lado: sin un nodo registrado **no existe ningún secreto válido**, así que en una instancia sin
nodos (Compulibra hoy) las rutas responden 401 a todo. Montarlas condicionalmente agregaría una bandera más que puede
quedar mal puesta, y el modo de fallar sería el peor posible: un nodo instalado que no puede sincronizar contra un
central que «debería» tener el endpoint.

## La conexión es por request

Se le pasa `get_connection` —la fábrica de LibraCore, la misma que usa el resto del producto— y no una conexión armada
(ver `create_sync_router` en LibraEdge).

## Qué se aplica

Un `Despachador` (libraedge ADR-007) con las cinco operaciones de venta de la capa ERP (`venta.registrada`,
`venta.pago_acreditado`, `venta.anulada`, `venta.devolucion`, `venta.facturada`; libracommerce ADR-067 y ADR-068) y las
cinco de la caja del nodo (`turno.abierto`, `turno.cerrado`, `caja.movimiento`, `caja.movimiento_anulado`, `dia.cerrado`;
libracommerce ADR-069), con los ganchos del producto. Lo que no tiene aplicador **no se marca aplicado**: va a revisión manual
(`libraedge-central revision listar|reintentar|descartar`, con
`LIBRAEDGE_DESPACHADOR=app.web.routers.sincronizacion_offline:despachador`).

Y las dos de stock (`stock.movimiento` y `compra.recibida`; libracommerce ADR-071): `registrar_en` registra los trece tipos. Contalibra no
tiene compras, así que en la práctica sólo sube `stock.movimiento` (los ajustes y las transferencias del nodo).

La carga inicial (`GET /sync/v1/carga-inicial`, libraedge ADR-023): al vincular, el nodo trae las existencias de **su** sucursal
(`offline_stock.carga_inicial_del_central`); la sucursal sale del nodo autenticado, no del pedido. Desde ahí el stock de esa
sucursal lo mueve sólo el nodo: el central contesta 409 (`app/web/app.py`).

El router además controla la versión del esquema (`version_de_alembic`: 409 si el nodo no está migrado igual que el
central) y le presta al nodo el ticket de ARCA (`libracore.nodo_offline.ta_para_el_nodo`, libraedge ADR-009): la clave
no sale del VPS.
"""

from libracommerce.erp import offline_stock
from libracommerce.erp.offline import registrar_en
from libracore.nodo_offline import ta_para_el_nodo
from libraedge.sync.api import create_sync_router
from libraedge.sync.despacho import Despachador
from libraedge.sync.esquema import version_de_alembic

from app.db_core import get_connection
from app.ganchos import GANCHOS


def armar_despachador() -> Despachador:
    """Las operaciones que el central de Contalibra sabe aplicar."""
    return registrar_en(Despachador(), GANCHOS)


despachador = armar_despachador()

router = create_sync_router(
    get_connection, despachador=despachador, version_esquema=version_de_alembic,
    prestar_ticket=ta_para_el_nodo, carga_inicial=offline_stock.carga_inicial_del_central,
)
