"""La fecha de negocio sale del reloj de Argentina del motor, no del proceso.

`libracore.fechas.hoy()` (ADR-070) es la fuente única: la fecha por defecto de un
remito o un presupuesto cargado desde la consola tiene que ser el día de
Argentina aunque el proceso corra en UTC —como los contenedores que no tienen
`TZ`— y sea de noche allá.

🔴 Con `date.today()` el día salía de la `TZ` del proceso: entre las 21:00 y la
medianoche de Argentina el comprobante quedaba fechado **mañana**. La suite
entera corre con `TZ=America/Argentina/Buenos_Aires` (ver `conftest.py`), así que
ningún otro test lo podía ver: éste vuelve el proceso a UTC y pisa el instante.
"""
import os
import time
from datetime import UTC, datetime

import pytest
from libracore import fechas

#: 02:30 UTC del 1 de abril de 2031 = 23:30 del 31 de marzo en Argentina. Una fecha
#: lejana a propósito: así `date.today()` nunca puede coincidir con la esperada.
INSTANTE = datetime(2031, 4, 1, 2, 30, tzinfo=UTC)
DIA_EN_ARGENTINA = "2031-03-31"


@pytest.fixture
def _proceso_en_utc_a_las_23_30_de_argentina(monkeypatch):
    """El proceso en UTC y el reloj del motor clavado en `INSTANTE`."""
    antes = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    monkeypatch.setattr(fechas, "_ahora_utc", lambda: INSTANTE)
    try:
        yield
    finally:
        if antes is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = antes
        time.tzset()


def test_la_fecha_por_defecto_del_remito_en_la_consola_es_la_de_argentina(
    _proceso_en_utc_a_las_23_30_de_argentina, monkeypatch,
):
    from app import main

    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    assert main.input_date("Fecha del remito") == DIA_EN_ARGENTINA


def test_una_fecha_escrita_a_mano_se_respeta(
    _proceso_en_utc_a_las_23_30_de_argentina, monkeypatch,
):
    """El control: el reloj sólo decide el valor por defecto, no pisa lo que se tipea."""
    from app import main

    monkeypatch.setattr("builtins.input", lambda _prompt: "2031-01-15")
    assert main.input_date("Fecha del presupuesto") == "2031-01-15"
