"""Los ganchos de Contalibra para la capa ERP de LibraCommerce.

Contalibra no tiene ganchos propios (`SIN_GANCHOS`: ni recetas ni pedidos). Desde E6 de LibraEdge (2026-10-19) los
que usan las ventas, el stock y el central son `con_outbox(SIN_GANCHOS, offline.OUTBOX)`: en un nodo offline cada venta
(en cualquier estado), cada pago acreditado, cada anulación y cada devolución se encolan para el central en la
transacción de la venta, y el número lleva el prefijo del nodo (`S02-V-00001`). **Fuera de un nodo son exactamente
`SIN_GANCHOS`**: `con_outbox` no encola nada ni cambia el número (lo sostiene
`tests/test_libraedge_fuera_de_un_nodo.py`).
"""

from __future__ import annotations

from libracommerce.erp import SIN_GANCHOS
from libracommerce.erp.offline import con_outbox

from app.offline import OUTBOX

#: Los ganchos de las ventas de este producto: los del motor con el outbox de LibraEdge (no-op fuera de un nodo).
GANCHOS = con_outbox(SIN_GANCHOS, OUTBOX)
