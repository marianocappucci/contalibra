"""La consulta de CUIT al padrón usa el par del ambiente que la instancia usa.

🔴 **Dos defectos en las mismas cuatro líneas, y el segundo es una regresión que
llega con el bump del pin.**

Este endpoint leía `arca["certificado_path"]` **directo**. Desde que una
instancia guarda dos pares de credenciales (LibraCore v1.71.0), esas columnas
—las que no llevan sufijo— son las de **producción**:

1. Autenticaba con el certificado **real** contra el WSAA de `arca["ambiente"]`.
   En una instancia de homologación, eso es firmar con la credencial del cliente
   creyendo que se prueba.
2. En una instancia de homologación —**las demos**— la migración `0007` mueve el
   par a las columnas con sufijo, así que las de producción quedan vacías y este
   endpoint contestaría **503 "Configurá los certificados"** sobre una instancia
   que los tiene perfectamente cargados. Es una regresión que el bump del pin
   introduce, no un defecto latente.

El barrido de accesos directos de LibraCore recorre el AST de `libracore/` y
**no ve este archivo**: vive en el producto. Un barrido cubre el árbol que
recorre.
"""

import pytest
from libracore import arca_credenciales
from libracore.config_manager import ARCHIVOS_POR_AMBIENTE
from libracore.db import arca_config as db_arca

CERT_HOMO, CLAVE_HOMO = ARCHIVOS_POR_AMBIENTE["homologacion"]
CERT_PROD, CLAVE_PROD = ARCHIVOS_POR_AMBIENTE["produccion"]


@pytest.fixture
def certs(tmp_path, monkeypatch):
    """Un `CERTS_DIR` con los cuatro archivos, cada uno con contenido distinto.

    🔑 Contenidos distintos y no un byte cualquiera: con los cuatro iguales,
    "usó el de homologación" y "usó el de producción" serían indistinguibles, y
    el test pasaría con el defecto puesto.
    """
    from libracore import config_manager

    d = tmp_path / "arca_certs"
    d.mkdir()
    for nombre in (CERT_HOMO, CLAVE_HOMO, CERT_PROD, CLAVE_PROD):
        (d / nombre).write_text(nombre)
    monkeypatch.setattr(config_manager, "CERTS_DIR", str(d))
    return d


@pytest.fixture
def solo_produccion(tmp_path, monkeypatch):
    """Un `CERTS_DIR` donde **sólo** existe el par de producción.

    🔑 El rescate de `resolve_cert_paths` cae al nombre estándar del ambiente si
    el archivo está ahí. Para afirmar *"no hay par de homologación"* tiene que
    de verdad no estar en disco: con el archivo presente el rescate lo encuentra
    —correctamente— y el test mediría otra cosa.
    """
    from libracore import config_manager

    d = tmp_path / "arca_certs"
    d.mkdir()
    for nombre in (CERT_PROD, CLAVE_PROD):
        (d / nombre).write_text(nombre)
    monkeypatch.setattr(config_manager, "CERTS_DIR", str(d))
    return d


def _config(certs, ambiente):
    """Una instancia como las que quedan después de la migración `0007`: cada
    par en las columnas de SU ambiente."""
    return {
        "empresa": "default", "cuit": "20111111119", "ambiente": ambiente,
        "certificado_path": str(certs / CERT_PROD),
        "clave_path": str(certs / CLAVE_PROD),
        "certificado_path_homologacion": str(certs / CERT_HOMO),
        "clave_path_homologacion": str(certs / CLAVE_HOMO),
    }


# -- Lo que el endpoint resuelve antes de salir a la red --------------------

def test_en_homologacion_usa_el_par_de_homologacion(certs):
    """🔴 El defecto que esto cierra: leyendo las columnas directo, acá salía
    el certificado **real del cliente**."""
    cert, clave = arca_credenciales.paths_en_disco(_config(certs, "homologacion"))
    assert cert == str(certs / CERT_HOMO), "usó el certificado de PRODUCCIÓN"
    assert clave == str(certs / CLAVE_HOMO)


def test_en_produccion_usa_el_par_de_produccion(certs):
    """El control del anterior: sin esto, una función que devolviera siempre el
    de homologación pasaría el test de arriba."""
    cert, clave = arca_credenciales.paths_en_disco(_config(certs, "produccion"))
    assert cert == str(certs / CERT_PROD)
    assert clave == str(certs / CLAVE_PROD)


def test_una_demo_migrada_NO_queda_sin_credenciales(certs):
    """🔴 La regresión que llega con el bump. Tras la `0007`, una instancia en
    homologación tiene las columnas de producción **vacías** — que es lo que el
    endpoint miraba para decidir si contestar 503."""
    cfg = {
        "empresa": "default", "cuit": "20111111119", "ambiente": "homologacion",
        "certificado_path": "", "clave_path": "",
        "certificado_path_homologacion": str(certs / CERT_HOMO),
        "clave_path_homologacion": str(certs / CLAVE_HOMO),
    }
    # Lo que el endpoint evalúa para decidir el 503.
    cert, clave = arca_credenciales.paths_en_disco(cfg)
    assert cert and clave, (
        "el endpoint contestaría 503 sobre una instancia que SÍ tiene su par")

    # Y el chequeo viejo, para dejar constancia de que era el que fallaba.
    assert not (cfg.get("certificado_path") and cfg.get("clave_path")), (
        "el control de este test no vale: las columnas de producción no están vacías")


def test_sin_ningun_par_sigue_dando_el_503(solo_produccion):
    """El otro lado: una instancia que de verdad no configuró ARCA tiene que
    seguir recibiendo el mensaje que la manda a Configuración.

    Usa `solo_produccion` y no `certs`: con el archivo de homologación **en
    disco** el rescate lo encuentra por nombre estándar aunque la columna esté
    vacía —que es justo para lo que el rescate existe—, y este test pasaría por
    la razón equivocada.
    """
    cfg = {"empresa": "default", "cuit": "", "ambiente": "homologacion"}
    assert arca_credenciales.paths_en_disco(cfg) == ("", "")


def test_el_par_del_otro_ambiente_no_alcanza(solo_produccion):
    """🔑 Tener cargado el de producción **no** habilita a consultar el padrón
    en homologación. Lo contrario es el defecto disfrazado de comodidad."""
    cfg = {
        "empresa": "default", "cuit": "20111111119", "ambiente": "homologacion",
        "certificado_path": str(solo_produccion / CERT_PROD),
        "clave_path": str(solo_produccion / CLAVE_PROD),
        "certificado_path_homologacion": "", "clave_path_homologacion": "",
    }
    assert arca_credenciales.paths_en_disco(cfg) == ("", "")

    # Control: el par de producción SÍ se encuentra. Sin esto, un `CERTS_DIR`
    # mal apuntado daría ("", "") y el test pasaría sin probar nada.
    assert arca_credenciales.paths_en_disco(cfg, "produccion")[0].endswith(CERT_PROD)


# -- El barrido: que no vuelva a aparecer un lector directo -----------------

def test_ningun_archivo_del_producto_lee_las_columnas_del_par():
    """🔴 El barrido de LibraCore recorre `libracore/` y **no llega acá**. Este
    es el mismo control, sobre el árbol de este producto.

    Se parsea el AST y no se grepea: los nombres aparecen en literales SQL y en
    los comentarios que explican esta misma asimetría.
    """
    import ast
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parents[1] / "app"
    columnas = {c for par in db_arca.COLUMNAS_POR_AMBIENTE.values() for c in par}
    culpables, mirados = [], 0
    for f in raiz.rglob("*.py"):
        mirados += 1
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
                    and n.slice.value in columnas):
                culpables.append(f"{f.relative_to(raiz)}:{n.lineno}")
            if (isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "get"
                    and n.args and isinstance(n.args[0], ast.Constant)
                    and n.args[0].value in columnas):
                culpables.append(f"{f.relative_to(raiz)}:{n.lineno}")

    assert mirados >= 30, f"el barrido sólo miró {mirados} archivos: ¿cambió la raíz?"
    assert not culpables, (
        "Estos leen las columnas del par sin pasar por `paths_en_disco()`:\n  "
        + "\n  ".join(culpables)
        + "\nLas columnas SIN sufijo son las de PRODUCCION."
    )


def test_el_barrido_reconoce_un_acceso_directo():
    """🔑 El control positivo: con el patrón mal escrito, el de arriba daría
    verde para siempre sin mirar nada."""
    import ast

    columnas = {c for par in db_arca.COLUMNAS_POR_AMBIENTE.values() for c in par}
    fuente = 'c = arca["certificado_path"]\nk = arca.get("clave_path")'
    hallados = []
    for n in ast.walk(ast.parse(fuente)):
        if (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
                and n.slice.value in columnas):
            hallados.append(n.slice.value)
        if (isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "get"
                and n.args and isinstance(n.args[0], ast.Constant)
                and n.args[0].value in columnas):
            hallados.append(n.args[0].value)
    assert sorted(hallados) == ["certificado_path", "clave_path"]
