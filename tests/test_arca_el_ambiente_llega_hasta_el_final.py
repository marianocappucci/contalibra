"""El ambiente llega hasta donde se usa: el padrón y la factura emitida.

🔴 **Este archivo existe porque mis primeros tests medían la capa equivocada.**
Llamaban a `libracore.arca_credenciales.paths_en_disco()` directamente, así que
verificaban la función **del motor** y no el código de este repo: tres de cuatro
mutaciones sobre `app/` sobrevivieron intactas.

Acá se entra por donde entra el usuario —el endpoint del padrón y el
`POST /api/ventas/{id}/facturar`— y se afirma sobre lo que sale.
"""

import datetime

import pytest
from libracore.config_manager import ARCHIVOS_POR_AMBIENTE

from app import database as db

CERT_HOMO, CLAVE_HOMO = ARCHIVOS_POR_AMBIENTE["homologacion"]
CERT_PROD, CLAVE_PROD = ARCHIVOS_POR_AMBIENTE["produccion"]

HOY = datetime.date.today().isoformat()


@pytest.fixture
def instancia_en_homologacion(tmp_path, monkeypatch):
    """Una instancia con **los dos pares** cargados y el selector en
    homologación — el estado exacto en el que se acompaña al cliente.

    🔑 Los dos pares, no uno: con sólo el de homologación, "usó el correcto" y
    "usó el único que había" son indistinguibles.
    """
    from libracore import config_manager

    d = tmp_path / "arca_certs"
    d.mkdir()
    for nombre in (CERT_HOMO, CLAVE_HOMO, CERT_PROD, CLAVE_PROD):
        (d / nombre).write_text(nombre)
    monkeypatch.setattr(config_manager, "CERTS_DIR", str(d))

    db.crear_arca_config(
        empresa="default", cuit="20111111119", punto_venta=1,
        clave_path=str(d / CLAVE_PROD), certificado_path=str(d / CERT_PROD),
        ambiente="homologacion",
    )
    db.actualizar_arca_config(
        "default",
        certificado_path_homologacion=str(d / CERT_HOMO),
        clave_path_homologacion=str(d / CLAVE_HOMO),
    )
    return d


# -- El padrón --------------------------------------------------------------

def test_el_padron_autentica_con_el_par_del_ambiente(
        admin_client, instancia_en_homologacion, monkeypatch):
    """🔴 El defecto: leyendo `arca["certificado_path"]` directo, este endpoint
    salía a autenticar con el certificado **de producción** —el real del
    cliente— contra el WSAA de homologación."""
    from app import arca_wsaa, arca_wspadron

    usados = {}

    async def _capturar(cert, clave, ambiente, servicio=""):
        usados.update(cert=cert, clave=clave, ambiente=ambiente)
        return {"token": "t", "sign": "s"}

    async def _padron(*a, **k):
        return {"razon_social": "Alguien SA"}

    monkeypatch.setattr(arca_wsaa, "autenticar", _capturar)
    monkeypatch.setattr(arca_wspadron, "consultar_persona", _padron)

    r = admin_client.get("/api/consultar-cuit/20111111119")
    assert r.status_code == 200, r.text

    assert usados["ambiente"] == "homologacion"
    assert usados["cert"].endswith(CERT_HOMO), (
        f"autenticó con {usados['cert']} — tiene que ser el par de homologación")
    assert usados["clave"].endswith(CLAVE_HOMO)


def test_el_padron_en_produccion_usa_el_par_real(
        admin_client, instancia_en_homologacion, monkeypatch):
    """El control del anterior: si el endpoint pidiera **siempre** el par de
    homologación, el test de arriba pasaría igual."""
    from app import arca_wsaa, arca_wspadron

    db.actualizar_arca_config("default", ambiente="produccion")
    usados = {}

    async def _capturar(cert, clave, ambiente, servicio=""):
        usados.update(cert=cert, ambiente=ambiente)
        return {"token": "t", "sign": "s"}

    monkeypatch.setattr(arca_wsaa, "autenticar", _capturar)
    monkeypatch.setattr(arca_wspadron, "consultar_persona",
                        lambda *a, **k: _ok())

    async def _ok():
        return {"razon_social": "Alguien SA"}

    r = admin_client.get("/api/consultar-cuit/20111111119")
    assert r.status_code == 200, r.text
    assert usados["ambiente"] == "produccion"
    assert usados["cert"].endswith(CERT_PROD)


def test_una_demo_migrada_puede_consultar_el_padron(
        admin_client, tmp_path, monkeypatch):
    """🔴 La regresión que trae el bump del pin. Tras la migración `0007`, una
    instancia en homologación tiene las columnas de producción **vacías** — que
    es lo que este endpoint miraba para decidir si contestar 503."""
    from app import arca_wsaa, arca_wspadron
    from libracore import config_manager

    d = tmp_path / "arca_certs"
    d.mkdir()
    for nombre in (CERT_HOMO, CLAVE_HOMO):
        (d / nombre).write_text(nombre)
    monkeypatch.setattr(config_manager, "CERTS_DIR", str(d))

    db.crear_arca_config(
        empresa="default", cuit="20111111119", punto_venta=1,
        clave_path="", certificado_path="", ambiente="homologacion",
    )
    db.actualizar_arca_config(
        "default",
        certificado_path_homologacion=str(d / CERT_HOMO),
        clave_path_homologacion=str(d / CLAVE_HOMO),
    )

    async def _capturar(cert, clave, ambiente, servicio=""):
        return {"token": "t", "sign": "s"}

    async def _padron(*a, **k):
        return {"razon_social": "Alguien SA"}

    monkeypatch.setattr(arca_wsaa, "autenticar", _capturar)
    monkeypatch.setattr(arca_wspadron, "consultar_persona", _padron)

    r = admin_client.get("/api/consultar-cuit/20111111119")
    assert r.status_code == 200, (
        "503 sobre una instancia que SÍ tiene su par cargado: " + r.text)


def test_sin_credenciales_sigue_dando_el_503(admin_client, tmp_path, monkeypatch):
    """El otro lado: una instancia que de verdad no configuró ARCA tiene que
    seguir recibiendo el mensaje que la manda a Configuración."""
    from libracore import config_manager

    d = tmp_path / "arca_certs"
    d.mkdir()
    monkeypatch.setattr(config_manager, "CERTS_DIR", str(d))

    r = admin_client.get("/api/consultar-cuit/20111111119")
    assert r.status_code == 503
    assert "Configurá los certificados" in r.json()["error"]


# -- La factura de una venta ------------------------------------------------

def _venta(client):
    resp = client.post("/api/ventas", json={
        "fecha": HOY,
        "items": [{"nombre": "Gaseosa", "qty": 1, "precio": 1000.0}],
        "pagos": [{"medio": "efectivo", "monto": 1000.0}],
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_la_factura_de_una_venta_registra_el_ambiente_con_el_que_se_numero(
        admin_client, monkeypatch):
    """🔴 Un comprobante emitido contra homologación trae CAE y numeración del
    WSFE de homologación. Sin marcarlo entra al Libro IVA del cliente y le rompe
    la correlatividad.

    🔑 Se parchea `get_next_numero_with_arca` porque la suite corre con
    `ENV=development`, donde ese llamado devuelve el string `"_dev_mock_"` y
    **todo sale `produccion`** — con eso, marcar bien y marcar siempre
    `produccion` dan idéntico resultado y la mutación es invisible. Fue
    exactamente lo que pasó: la mutación sobrevivió.
    """
    from app import venta_facturacion

    async def _numero_de_homologacion(punto_venta, tipo):
        return 501, None, {"ambiente": "homologacion", "cuit": "20111111119"}

    monkeypatch.setattr(venta_facturacion, "get_next_numero_with_arca",
                        _numero_de_homologacion)

    venta = _venta(admin_client)
    r = admin_client.post(f"/api/ventas/{venta['id']}/facturar")
    assert r.status_code == 200, r.text

    factura = db.get_factura(r.json()["factura"]["id"])
    assert factura["ambiente"] == "homologacion", (
        "la factura quedó marcada como real: entra al Libro IVA del cliente")


def test_y_en_produccion_la_marca_como_real(admin_client, monkeypatch):
    """El control positivo: sin esto, marcar **todo** como homologación pasaría
    el test de arriba — y sacaría del Libro IVA los comprobantes reales, que es
    el peor de los dos errores."""
    from app import venta_facturacion

    async def _numero_real(punto_venta, tipo):
        return 84, None, {"ambiente": "produccion", "cuit": "20111111119"}

    monkeypatch.setattr(venta_facturacion, "get_next_numero_with_arca", _numero_real)

    venta = _venta(admin_client)
    r = admin_client.post(f"/api/ventas/{venta['id']}/facturar")
    assert r.status_code == 200, r.text

    assert db.get_factura(r.json()["factura"]["id"])["ambiente"] == "produccion"


def test_sin_arca_configurado_la_factura_es_real(admin_client, monkeypatch):
    """Sin ARCA no hay CAE y el número es el de la propia instancia: ese
    comprobante **es** el real del cliente y tiene que entrar al Libro IVA."""
    from app import venta_facturacion

    async def _sin_arca(punto_venta, tipo):
        return 1, None, None

    monkeypatch.setattr(venta_facturacion, "get_next_numero_with_arca", _sin_arca)

    venta = _venta(admin_client)
    r = admin_client.post(f"/api/ventas/{venta['id']}/facturar")
    assert r.status_code == 200, r.text
    assert db.get_factura(r.json()["factura"]["id"])["ambiente"] == "produccion"
