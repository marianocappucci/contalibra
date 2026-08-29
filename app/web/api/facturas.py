"""La API de comprobantes de Contalibra: facturas, notas de crédito y de débito.

Los doce endpoints **ya no viven acá**: los arma `libracore.facturas_router`
desde el 2026-08-27. Estaban escritos enteros en este archivo y otra vez en el
de Restolibra, y las dos copias se diffearon antes de unificarlas: las
divergencias reales eran cuatro, y de este producto sólo una —cerrar los ítems
de la bandeja de MercadoPago que la factura vino a cubrir—.

Eso es lo único que queda acá, como hook, más los dos gates y el texto que dice
dónde se configura el SMTP en **este** producto.

> El PDF (`GET /facturas/{id}/pdf`), el ticket y el recibo siguen en
> `web/routers/facturas.py` sin tocar: son descargas autenticadas por cookie que
> la SPA linkea directo, y no entraron a la extracción.
"""

import logging

from libracore.db import comprobantes_pendientes
from libracore.facturas_router import build_comprobantes_router

from app.web.api_auth import get_current_user_json, require_role_json

logger = logging.getLogger(__name__)


def _cerrar_pendientes_de_la_bandeja(factura_id: int, datos: dict, usuario: dict) -> None:
    """Marca como facturados los comprobantes de la bandeja que ésta cubrió.

    Los ids llegan armados por `POST /api/comprobantes-pendientes/facturar-prefill`
    y viajan escondidos en el formulario: el usuario ve los ítems, no los ids.

    🔑 **Cada id va en su propio `try`.** Si uno falla, los demás se marcan
    igual; lo que quede sin marcar sigue visible en la bandeja, que es el peor
    caso tolerable —se ve y se resuelve a mano—. El motor además envuelve todo
    este hook, así que un error tampoco puede tumbar una emisión ya autorizada
    por ARCA.
    """
    ids = datos.get("comprobantes_pendientes_ids") or []
    if not ids:
        return
    quien = usuario.get("nombre") or usuario.get("username") or ""
    for comprobante_id in ids:
        try:
            comprobantes_pendientes.marcar_facturado(comprobante_id, factura_id, quien)
        except Exception:
            logger.exception(
                "No se pudo marcar el comprobante pendiente %s como facturado "
                "por la factura %s", comprobante_id, factura_id,
            )


router = build_comprobantes_router(
    usuario_actual=get_current_user_json,
    solo_admin=require_role_json("admin"),
    al_emitir=_cerrar_pendientes_de_la_bandeja,
    # En este producto el SMTP se carga en Configuración → Email. Restolibra lo
    # tiene en Integraciones, y mandar a la solapa equivocada es peor que no
    # decir nada.
    donde_configurar_smtp="Configuración → Email",
)
