"""La empresa ficticia de la demo pública (ADR-038 de libracore).

En una demo (`DEMO_MODE=1`) el motor nunca muestra los datos de la empresa que
haya en `config.json`: los pisa con la empresa que el producto registre acá.
Es ficticia de punta a punta —CUIT con dígito verificador válido y prefijo
`30-999` que ARCA no asigna, correo en `.example`— y su logo viaja con la
imagen, no con `DATA_DIR`, que es justo lo que se ensucia. Motivo: el
2026-10-09 una demo de la suite mostraba los datos fiscales de un cliente real.

Fuera de una demo, registrar no cambia nada.
"""
from pathlib import Path

from libracore import config_manager

#: El logo de fantasía de una distribuidora inventado, en `app/assets/`.
LOGO = Path(__file__).parent / "assets" / "logo-empresa-demo.png"

EMPRESA = {
    "empresa_nombre":             "Insumos del Plata SRL",
    "empresa_cuit":               "30-99999901-4",
    "empresa_direccion":          "Av. Ficticia 1234, CABA",
    "empresa_telefono":           "011 4000-0000",
    "empresa_email":              "ventas@insumosdelplata.example",
    "empresa_iibb":               "901-000000-1",
    # Las facturas de la demo son C: el emisor tiene que ser monotributista.
    "empresa_iva_condition":      "Monotributista",
    "empresa_inicio_actividades": "2015-03-01",
}


def registrar() -> None:
    """Idempotente: se puede llamar en cada arranque."""
    config_manager.usar_empresa_demo(EMPRESA, logo_path=str(LOGO))
