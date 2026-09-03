"""El cron de MercadoPago tiene que resolver el cliente como todos los demas.

`resolver_cliente_pago` existe desde el 2026-07-13 para que un pago que llega
con un CUIT/email distinto al del cliente se facture igual al cliente correcto.
La regla es que NINGUN camino que emita una factura de MP resuelva el cliente
por su cuenta. `scripts/sync_mp_auto.py` -- el cron nocturno, que es el que
emite la mayoria de las facturas sin que nadie mire -- se habia quedado afuera:
matcheaba a mano por email y despues por CUIT.

Se cobro dos veces, las dos con plata y CAE de por medio:

- 2026-07-10: el pago de AGROPECUARIA RIPEHO se facturo a PATRICIA SCOVENNA
  (0005-00000036), anulada despues con la NC 0005-00000004.
- 2026-08-03: el pago de MARIANO MARTIN VISCO se facturo a un cliente
  placeholder cuya razon social era el propio email del pagador y que no tenia
  CUIT (0005-00000050). El alias que lo hubiera impedido estaba cargado desde
  el 2026-07-16.

El detalle que convierte el atajo en un bug: `get_client_by_email` desempata
con `id DESC`, asi que ante dos clientes con el mismo email gana el mas nuevo
-- y el mas nuevo suele ser justo el placeholder "Consumidor Final" que creo el
fallback de `generar_factura_mp` la primera vez que el pago no matcheo.
"""
import asyncio
import importlib.util
from pathlib import Path

# 🔑 Se parchea `libracore.mp_api` y NO `app.mp_api`.
#
# `app/mp_api.py` es un shim (`from libracore.mp_api import ...`), asi que
# su atributo es un binding DISTINTO. Desde que el sync vive en el motor,
# parchear el del producto no intercepta nada y el test sale a la API real
# de MercadoPago -- da 401 y el caso se lee como "no facturo".
from libracore import mp_api

from app import config_manager
from app import database as db

RAIZ = Path(__file__).resolve().parent.parent

EMAIL      = "mariano@metalmaxsoluciones.com.ar"
CUIT_REAL  = "20-31781916-2"
CUIT_PAGO  = "20317819162"
MOV_ID     = "170841255119"


def _cargar_sync():
    """El script vive fuera del paquete y corre por ruta desde cron, asi que
    se carga igual que lo hace el contenedor: por archivo."""
    spec = importlib.util.spec_from_file_location(
        "sync_mp_auto_bajo_test", RAIZ / "scripts" / "sync_mp_auto.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _clientes_con_email_duplicado():
    """El cliente real y, con id mas alto, el placeholder que dejo el fallback
    de `generar_factura_mp` -- el escenario exacto de produccion."""
    real = db.create_client(
        name="MARIANO MARTIN VISCO", cuit_dni=CUIT_REAL,
        email=EMAIL, iva_condition="Responsable Inscripto",
    )
    placeholder = db.create_client(
        name=EMAIL, email=EMAIL, iva_condition="Consumidor Final",
    )
    assert placeholder > real, "el placeholder tiene que ser el mas nuevo"
    return real, placeholder


def test_el_alias_le_gana_al_placeholder_mas_nuevo(client):
    """Por que el atajo fallaba: el match directo por email elige el id mas
    alto, el alias elige el cliente que el usuario configuro."""
    real, placeholder = _clientes_con_email_duplicado()
    assert db.get_client_by_email(EMAIL)["id"] == placeholder

    db.crear_alias_facturacion("email", EMAIL, real)
    assert db.resolver_cliente_pago(EMAIL, CUIT_PAGO)["id"] == real


def test_el_cron_le_factura_al_cliente_del_alias(client, monkeypatch):
    """El caso completo, de punta a punta por el mismo camino que corre de
    madrugada: un pago de MP con alias configurado tiene que salir facturado
    al cliente real, con su razon social y su CUIT."""
    real, _ = _clientes_con_email_duplicado()
    db.crear_alias_facturacion("email", EMAIL, real)

    cfg = config_manager.load()
    cfg["mp_access_token"] = "token-de-suite"
    config_manager.save(cfg)

    pago = {
        "id": MOV_ID,
        "collector_id": 123,
        "transaction_amount": 10500.0,
        "description": "Hosting Mensual 02",
        "payment_type_id": "credit_card",
        "payment_method_id": "master",
        "date_approved": "2026-08-02T10:00:00.000-03:00",
        "payer": {
            "email": EMAIL, "first_name": "", "last_name": "",
            "identification": {"type": "CUIT", "number": CUIT_PAGO},
        },
    }

    async def _info(_token):
        return {"id": 123, "email": "cobrador@compulibra.com.ar"}

    async def _movs(_token, _desde, _hasta):
        return [pago]

    monkeypatch.setattr(mp_api, "obtener_usuario_info", _info)
    monkeypatch.setattr(mp_api, "obtener_movimientos", _movs)

    # `main()` corre el `asyncio.run` por dentro: es exactamente lo que
    # ejecuta el cron, sin un camino de test paralelo.
    resultado = _cargar_sync().main(["--dias", "2"])
    assert resultado["facturados"] == 1, resultado

    mov = db.get_mp_movimiento_by_mp_id(MOV_ID)
    assert mov["estado_factura"] == "facturado"

    factura = db.get_factura(mov["factura_id"])
    assert factura["cliente_razon"] == "MARIANO MARTIN VISCO", (
        "el cron facturo al placeholder: volvio a resolver el cliente por su cuenta"
    )
    assert factura["cliente_cuit"] == CUIT_REAL
    # 1 = Responsable Inscripto. El placeholder hubiera dejado 5 (Consumidor
    # Final), que es lo que mostraba el PDF que reclamo el cliente.
    assert factura["cliente_iva_cond"] == 1
