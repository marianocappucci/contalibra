"""API JSON de Presupuestos: los siete endpoints los arma
`libracore.presupuestos_router.build_presupuestos_router` desde v1.83.0 (eran
byte-idénticos con Restolibra salvo la conversión a remito). Acá sólo se inyecta
lo del producto: la auth, el PDF, la conversión (con la elección valorizado/
pelado, propia de Contalibra), el envío de email y el formato de moneda. El PDF
por descarga (`GET /presupuestos/{id}/pdf`) sigue en `web/routers/presupuestos.py`."""
from libracore.presupuestos_router import build_presupuestos_router

from app import database as db
from app import pdf_generator as pdf_gen
from app.web.api_auth import get_current_user_json
from app.web.helpers.email_helper import send_comprobante, smtp_configurado
from app.web.templates_config import _moneda


def _convertir_a_remito(presupuesto: dict, valorizado: bool = False):
    # La conversión vive en el motor (libracore.convertir_presupuesto_a_remito);
    # acá se enchufa el PDF del producto y la elección valorizado/pelado.
    if valorizado:
        # Hereda los precios del presupuesto y los MUESTRA en el PDF.
        db.convertir_presupuesto_a_remito(
            presupuesto,
            generar_pdf=lambda r: pdf_gen.generate_pdf(r, show_prices=True),
        )
    else:
        # Nota de entrega pelada: se tiran los precios (ítems description+qty,
        # totales en 0) para que ni los datos ni el PDF los muestren.
        pelado = {
            **presupuesto,
            "items": [
                {"description": i["description"], "qty": i["qty"]}
                for i in presupuesto["items"]
            ],
            "subtotal": 0, "tax_rate": 0, "tax_amount": 0, "total": 0,
        }
        db.convertir_presupuesto_a_remito(pelado, generar_pdf=pdf_gen.generate_pdf)


router = build_presupuestos_router(
    usuario_actual=get_current_user_json,
    generar_pdf=pdf_gen.generate_pdf_presupuesto,
    convertir_a_remito=_convertir_a_remito,
    smtp_configurado=smtp_configurado,
    enviar_comprobante=send_comprobante,
    moneda=_moneda,
    donde_configurar_smtp="Configuración → Email",
)
