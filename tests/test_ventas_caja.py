"""Ventas POS (crear_venta_directa: la transaccion que cruza
LibraCommerce y LibraCore en un solo commit) + turnos de caja."""
import datetime

HOY = datetime.date.today().isoformat()


def _venta(client, items=None, pagos=None, **extra):
    payload = {
        "fecha": HOY,
        "items": items or [{"nombre": "Producto suelto", "qty": 2, "precio": 100.0}],
        "pagos": pagos or [{"medio": "efectivo", "monto": 200.0}],
    }
    payload.update(extra)
    resp = client.post("/api/ventas", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_medios_pago(admin_client):
    medios = admin_client.get("/api/ventas/medios-pago").json()
    assert any(m["id"] == "efectivo" for m in medios)


def test_venta_cobrada(admin_client):
    venta = _venta(admin_client)
    assert venta["total"] == 200.0
    assert venta["estado"] == "cobrada"


def test_venta_sin_items_422(admin_client):
    resp = admin_client.post("/api/ventas", json={
        "fecha": HOY, "items": [], "pagos": [{"medio": "efectivo", "monto": 100}]})
    assert resp.status_code == 422


def test_venta_sin_pagos_422(admin_client):
    resp = admin_client.post("/api/ventas", json={
        "fecha": HOY, "items": [{"nombre": "X", "qty": 1, "precio": 100}], "pagos": []})
    assert resp.status_code == 422


def test_venta_con_pago_parcial(admin_client):
    venta = _venta(admin_client,
                   items=[{"nombre": "Caro", "qty": 1, "precio": 1000.0}],
                   pagos=[{"medio": "efectivo", "monto": 400.0}])
    assert venta["estado"] == "parcial"


def test_venta_con_descuento(admin_client):
    venta = _venta(admin_client,
                   items=[{"nombre": "X", "qty": 1, "precio": 1000.0}],
                   pagos=[{"medio": "efectivo", "monto": 900.0}],
                   descuento=100.0)
    assert venta["total"] == 900.0
    assert venta["estado"] == "cobrada"


def test_descuento_no_supera_el_subtotal(admin_client):
    venta = _venta(admin_client,
                   items=[{"nombre": "X", "qty": 1, "precio": 100.0}],
                   pagos=[{"medio": "efectivo", "monto": 1.0}],
                   descuento=5000.0)
    assert venta["total"] == 0.0


def test_venta_descuenta_stock(admin_client):
    p = admin_client.post("/api/productos", json={
        "nombre": "Fideos", "precio_venta": 500.0, "precio_costo": 300.0}).json()
    admin_client.post(f"/api/stock/{p['id']}/ajuste", json={"modo": "absoluto", "cantidad": 20})
    _venta(admin_client,
           items=[{"nombre": "Fideos", "qty": 3, "precio": 500.0, "producto_id": p["id"]}],
           pagos=[{"medio": "efectivo", "monto": 1500.0}])
    assert admin_client.get(f"/api/stock/{p['id']}").json()["stock_actual"] == 17


def test_detalle_y_listado(admin_client):
    venta = _venta(admin_client, observaciones="venta de prueba")
    detalle = admin_client.get(f"/api/ventas/{venta['id']}").json()
    assert detalle["id"] == venta["id"]
    listado = admin_client.get("/api/ventas").json()
    assert any(v["id"] == venta["id"] for v in listado)


def test_detalle_inexistente_404(admin_client):
    assert admin_client.get("/api/ventas/99999").status_code == 404


def test_anular_es_admin_only(admin_client):
    venta = _venta(admin_client)
    admin_client.post("/api/usuarios", json={
        "username": "vendedor", "nombre": "V", "password": "clave-123456", "role": "operador"})
    admin_client.post("/api/logout")
    admin_client.post("/api/login", json={"username": "vendedor", "password": "clave-123456"})
    assert admin_client.post(f"/api/ventas/{venta['id']}/anular").status_code == 403


def test_anular_venta(admin_client):
    venta = _venta(admin_client)
    anulada = admin_client.post(f"/api/ventas/{venta['id']}/anular")
    assert anulada.status_code == 200
    assert anulada.json()["estado"] == "anulada"


def test_anular_devuelve_stock(admin_client):
    p = admin_client.post("/api/productos", json={
        "nombre": "Retornable", "precio_venta": 100.0, "precio_costo": 50.0}).json()
    admin_client.post(f"/api/stock/{p['id']}/ajuste", json={"modo": "absoluto", "cantidad": 10})
    venta = _venta(admin_client,
                   items=[{"nombre": "Retornable", "qty": 4, "precio": 100.0, "producto_id": p["id"]}],
                   pagos=[{"medio": "efectivo", "monto": 400.0}])
    admin_client.post(f"/api/ventas/{venta['id']}/anular")
    assert admin_client.get(f"/api/stock/{p['id']}").json()["stock_actual"] == 10


def test_turno_abrir_y_cerrar(admin_client):
    abierto = admin_client.post("/api/turnos/abrir", json={"monto_inicial": 5000.0})
    assert abierto.status_code == 200, abierto.text
    tid = abierto.json()["id"]
    detalle = admin_client.get(f"/api/turnos/{tid}")
    assert detalle.status_code == 200
    cerrado = admin_client.post(f"/api/turnos/{tid}/cerrar", json={"monto_declarado": 5000.0})
    assert cerrado.status_code == 200


def test_no_abrir_dos_turnos_a_la_vez(admin_client):
    primero = admin_client.post("/api/turnos/abrir", json={"monto_inicial": 1000.0})
    assert primero.status_code == 200
    segundo = admin_client.post("/api/turnos/abrir", json={"monto_inicial": 1000.0})
    # Con un turno ya abierto, abrir otro no debe crear un segundo turno
    # activo (409/422) -- si la API lo permite devolviendo el mismo, tiene
    # que ser el mismo id.
    if segundo.status_code == 200:
        assert segundo.json()["id"] == primero.json()["id"]
    else:
        assert segundo.status_code in (409, 422)


# ── El movimiento de caja se escribe al ACREDITAR, no al declarar ────────────
#
# 🔴 El defecto que esto cierra: hasta el 2026-08-31 `crear_venta_directa`
# escribia un movimiento de caja por cada medio en el momento de crear la
# venta. Una venta que se cobra por QR metia la plata en la caja **antes de que
# nadie escaneara nada**, asi que si el cliente no pagaba el arqueo del turno
# cerraba con plata que no entro -- y el error aparecia horas despues.


def _ingresos_en_caja():
    """Cuantos movimientos de ingreso tiene la caja, leidos de la TABLA.

    Se mide la tabla y no un endpoint: lo que este paso afirma es que la caja
    no se escribe, y un endpoint mete su propia forma --filtros, permisos,
    paginado-- entre la afirmacion y el hecho.
    """
    from app.db_core import get_connection
    with get_connection() as c:
        return c.execute(
            "SELECT count(*) FROM caja_movimientos WHERE tipo=?", ("ingreso",)
        ).fetchone()[0]


def test_un_pago_pendiente_NO_escribe_movimiento_de_caja(admin_client, monkeypatch):
    """🔴 El gate del paso: la caja no se mueve por un pago que no entro.

    Se crea la venta pasando el pago como `pendiente` --que es lo que va a
    hacer el cobro por QR-- y se mide la caja antes y despues. Tiene que dar
    exactamente lo mismo.
    """
    from app import database as db

    antes = _ingresos_en_caja()

    venta_id = db.crear_venta_directa(
        fecha=HOY,
        items=[{"nombre": "Con QR", "qty": 1, "precio": 500.0}],
        subtotal=500.0, descuento=0.0, total=500.0,
        cliente_id=None, cliente_nombre="", usuario_id=None, observaciones="",
        estado="pendiente",
        pagos=[{"medio": "mercadopago", "monto": 500.0, "referencia": "",
                "estado": "pendiente"}],
        stock_habilitado=False,
    )
    assert venta_id

    despues = _ingresos_en_caja()
    assert despues == antes, (
        "un pago pendiente escribio un movimiento de caja: la venta todavia no "
        "se cobro y el arqueo ya la cuenta")


def test_un_pago_aprobado_SI_escribe_movimiento_de_caja(admin_client):
    """El control positivo, y no es decorativo: sin el, una implementacion que
    no escribiera NINGUN movimiento dejaria el test de arriba en verde y
    rompería la caja de todas las ventas."""
    from app import database as db

    antes = _ingresos_en_caja()

    db.crear_venta_directa(
        fecha=HOY,
        items=[{"nombre": "En efectivo", "qty": 1, "precio": 700.0}],
        subtotal=700.0, descuento=0.0, total=700.0,
        cliente_id=None, cliente_nombre="", usuario_id=None, observaciones="",
        estado="cobrada",
        pagos=[{"medio": "efectivo", "monto": 700.0, "referencia": "",
                "estado": "aprobado"}],
        stock_habilitado=False,
    )

    despues = _ingresos_en_caja()
    assert despues == antes + 1


def test_la_venta_del_POS_sigue_cobrando_como_hoy(admin_client):
    """Este paso NO cambia el comportamiento del mostrador.

    El POS declara sus pagos como `aprobado` --el cajero vio la plata-- asi que
    la venta sigue naciendo cobrada y con su movimiento de caja. Lo que cambia
    despues es el cobro por QR.
    """
    antes = _ingresos_en_caja()
    venta = _venta(admin_client)
    assert venta["estado"] == "cobrada"
    assert _ingresos_en_caja() == antes + 1


def test_un_pago_sin_estado_no_entra(admin_client):
    """🔴 El hueco que dejo abierto la migracion, cerrado en el camino de
    escritura.

    La columna tiene default `'aprobado'` --lo necesita el backfill de las
    filas viejas-- asi que un INSERT que la omita contaria como plata que
    entro sin que nadie lo decida. Aca el estado se declara o revienta.
    """
    from app import database as db
    from libracore import pagos as acreditacion

    import pytest
    with pytest.raises(acreditacion.PagoSinEstado):
        db.crear_venta_directa(
            fecha=HOY,
            items=[{"nombre": "Sin estado", "qty": 1, "precio": 100.0}],
            subtotal=100.0, descuento=0.0, total=100.0,
            cliente_id=None, cliente_nombre="", usuario_id=None,
            observaciones="", estado="cobrada",
            pagos=[{"medio": "efectivo", "monto": 100.0, "referencia": ""}],
            stock_habilitado=False,
        )
