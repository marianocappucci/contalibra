"""Ningun DEFAULT del DDL de Contalibra estampa una hora que no sea la de Argentina.

🔴 **El defecto que cubre no daba error y estuvo desde siempre.** El DEFAULT de
las columnas `created_at`/`updated_at` era `datetime('now')`, que en
SQLite es UTC y que el adaptador de PostgreSQL traduce a UTC **a proposito**,
para que las dos bases guarden el mismo texto. O sea que las dos guardaban la
hora equivocada, y de la misma manera. Lo creado entre las 21:00 y la medianoche
quedaba fechado el dia siguiente.

Se midio en la instancia `compulibra` de Contalibra el 2026-08-29 y se barrieron
las 19 bases del VPS con schema de LibraCore: las 19 en UTC. Ver la revision
`0003` de [[libracore]] para el diagnostico completo.

🔑 **El barrido vive en el motor, no aca.** `defaults_fuera_de_hora_ar()` es la
misma funcion que corren LibraCore y los otros tres productos con DDL propio.
Copiar la regex en cada repo es la forma conocida de que empiecen a decir cosas
distintas: paso con las cinco definiciones de "hoy" del frontend, y solo tres
fijaban la zona.

🔑 **Y mira la PROPIEDAD final**, no el patron viejo: "ninguna columna con reloj
queda fuera de la hora de Argentina". Buscar `datetime('now')` dejaria pasar una
columna nueva escrita como `DEFAULT CURRENT_TIMESTAMP`, que tiene el mismo
problema con otra cara.
"""
import pathlib
from pathlib import Path

import pytest
from libracore.db.schema import defaults_con_reloj, defaults_fuera_de_hora_ar

RAIZ = Path(__file__).resolve().parents[1]

#: Se barren los directorios, no una lista de archivos escrita a mano: un DDL
#: nuevo en un modulo nuevo tiene que entrar solo. Las revisiones ya aplicadas
#: quedan afuera porque son historia y no se tocan.
_DIRECTORIOS = ('app',)
_EXCLUIR = ("__pycache__", "/migrations/versions/", "/tests/")


def _fuentes():
    for sub in _DIRECTORIOS:
        for archivo in sorted((RAIZ / sub).rglob("*.py")):
            if any(x in str(archivo) for x in _EXCLUIR):
                continue
            yield archivo


def test_el_barrido_lee_los_fuentes():
    """Control: sin esto, una lista vacia pasaria por verde para siempre.

    Es el mismo control que lleva la guarda del motor. Un barrido que dejo de
    encontrar archivos —porque el DDL se movio de carpeta, por ejemplo— informa
    "limpio" sobre un repo que no miro.

    🔑 **Hasta P9-M5 este control contaba columnas con reloj y exigia al menos
    una. Dejo de poder hacerlo el 2026-09-07, y no por un defecto.** La unica que
    le quedaba a Contalibra estaba dentro de `_migrar_ventas_pagos_a_sales`, el
    rebuild de `ventas_pagos` que se retiro cuando esa migracion paso a ser
    `libracommerce.erp.ventas.repuntar_fk_ventas_pagos`. Hoy el DDL propio del
    producto son tres tablas sin timestamps y el resto lo declaran los motores,
    que corren **esta misma** funcion sobre sus fuentes. Un piso de cero no
    controla nada, asi que el control pasa a mirar lo que sigue existiendo: que
    el barrido lea archivos, y que los lea de verdad. La guarda de abajo queda
    como tripwire para el dia que alguien vuelva a declarar DDL con reloj aca.
    """
    archivos = list(_fuentes())
    # 73 al 2026-09-07; el piso solo tiene que distinguir "barrio" de "no barrio".
    assert len(archivos) >= 40, f"el barrido leyo solo {len(archivos)} archivos"
    # Y que los lea de verdad, no como cadenas vacias: es la otra mitad del
    # falso verde barato.
    assert any("def " in f.read_text(encoding="utf-8") for f in archivos)
    # Los motores si tienen que tener DDL con reloj: si esta funcion dejara de
    # encontrar nada en ninguna parte, seria ella la rota.
    from libracore.db import schema as schema_core

    assert defaults_con_reloj(pathlib.Path(schema_core.__file__).read_text(encoding="utf-8"))


@pytest.mark.parametrize("archivo", sorted(_fuentes()), ids=lambda f: f.name)
def test_ninguna_columna_estampa_una_hora_que_no_sea_la_de_argentina(archivo):
    fuera = defaults_fuera_de_hora_ar(archivo.read_text(encoding="utf-8"))
    assert fuera == [], (
        f"{archivo.relative_to(RAIZ)} declara columnas con una hora que no es la "
        "de Argentina:\n" + "\n".join(fuera)
    )
