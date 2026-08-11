"""Recibos: el comprobante del cobro, de punta a punta por la API real.

Lo que se prueba acá no es la lógica de emisión —eso está en la suite de
LibraCore, con dobles— sino **el cableado del producto**: que el pago de
cuenta corriente emita solo, que la venta use el `get_venta` de Contalibra
(sus ventas viven en `sales`, no en `ventas`), que el PDF salga por HTTP y
que anular no toque la plata.
"""
import datetime
import io
import re

from pypdf import PdfReader

HOY = datetime.date.today().isoformat()


def _cliente(client, name="Almacen Don Pepe", **extra):
    resp = client.post("/api/clientes", json={"name": name, **extra})
    assert resp.status_code == 200, resp.text
    return resp.json()


_cuits = iter(range(20304050607, 20304060000))


def _deudor(client, name, monto=1000.0):
    """Cliente con deuda real: la venta fiada es la que la genera.

    El CUIT sale de un contador, no de un literal: `create_client` rechaza
    duplicados desde el fix de clientes duplicados (2026-07-13), así que un
    test con dos deudores y un CUIT fijo falla por el guard, no por el recibo.
    """
    c = _cliente(client, name, cuit_dni=str(next(_cuits)))
    resp = client.post("/api/ventas", json={
        "fecha": HOY, "cliente_id": c["id"],
        "items": [{"nombre": "Mercaderia", "qty": 1, "precio": monto}],
        "pagos": [{"medio": "cuenta_corriente", "monto": monto}],
    })
    assert resp.status_code == 200, resp.text
    return c


def _texto_del_pdf(contenido: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(contenido)).pages)


def _sin_la_hora_de_generacion(pdf: bytes) -> bytes:
    """El mismo PDF generado dos veces difiere en dos campos que llevan la hora:
    `/CreationDate` y el `/ID`, que deriva de ella.

    🔴 Sin esto el test es **flaky y no lo parece**: compara byte a byte, y sólo
    falla cuando las dos generaciones caen a los dos lados de un segundo.
    Frenó dos deploys el 2026-08-11, las dos veces con el mismo commit dando
    verde en otro run — o sea que el rojo no decía nada del código.

    Se saca sólo eso: todo el resto del documento se sigue comparando byte a
    byte, que es lo que hace fuerte a este test.
    """
    pdf = re.sub(rb"/CreationDate \(D:[0-9]+Z?\)", b"/CreationDate ()", pdf)
    pdf = re.sub(rb"/ID \[<[0-9A-Fa-f]+><[0-9A-Fa-f]+>\]", b"/ID []", pdf)
    return pdf


# ── Cobranza de cuenta corriente ─────────────────────────────────────────────

def test_el_pago_de_cuenta_corriente_emite_su_recibo_solo(admin_client):
    """Quien cobra tiene al cliente enfrente esperando el papel: no puede
    depender de que después se acuerde de apretar otro botón."""
    c = _deudor(admin_client, "Emite solo")
    resp = admin_client.post(f"/api/cuenta-corriente/{c['id']}/pagar",
                             json={"monto": 1000.0, "fecha": HOY})
    assert resp.status_code == 200, resp.text
    assert resp.json()["recibo_id"] is not None


def test_el_recibo_emitido_al_cobrar_sale_en_el_listado(admin_client):
    c = _deudor(admin_client, "Listado")
    recibo_id = admin_client.post(f"/api/cuenta-corriente/{c['id']}/pagar",
                                  json={"monto": 1000.0, "fecha": HOY}).json()["recibo_id"]

    listado = admin_client.get("/api/recibos").json()
    encontrado = [r for r in listado["recibos"] if r["id"] == recibo_id]
    assert len(encontrado) == 1
    assert encontrado[0]["numero_visible"] == "0001-00000001"
    assert encontrado[0]["origen_tipo"] == "cc_pago"
    assert encontrado[0]["total"] == 1000.0
    assert encontrado[0]["cliente_razon"] == "Listado"
    assert encontrado[0]["anulado"] is False


def test_pedir_el_recibo_de_una_cobranza_dos_veces_no_emite_dos(admin_client):
    """El botón de la grilla llama a este endpoint sin saber si ya existe."""
    c = _deudor(admin_client, "Idempotente")
    admin_client.post(f"/api/cuenta-corriente/{c['id']}/pagar",
                      json={"monto": 1000.0, "fecha": HOY})
    movimientos = admin_client.get(f"/api/cuenta-corriente/{c['id']}").json()["movimientos"]
    pago_id = next(m["cc_pago_id"] for m in movimientos if m["cc_pago_id"])

    primero = admin_client.post(f"/api/recibos/cobranza/{pago_id}").json()
    segundo = admin_client.post(f"/api/recibos/cobranza/{pago_id}").json()
    assert primero["id"] == segundo["id"]
    assert admin_client.get("/api/recibos").json()["total"] == 1


def test_borrar_el_pago_anula_su_recibo(admin_client):
    """Si no, queda un comprobante vigente de un cobro que el sistema ya no
    reconoce."""
    c = _deudor(admin_client, "Se arrepiente")
    recibo_id = admin_client.post(f"/api/cuenta-corriente/{c['id']}/pagar",
                                  json={"monto": 1000.0, "fecha": HOY}).json()["recibo_id"]
    movimientos = admin_client.get(f"/api/cuenta-corriente/{c['id']}").json()["movimientos"]
    pago_id = next(m["cc_pago_id"] for m in movimientos if m["cc_pago_id"])

    assert admin_client.delete(f"/api/cuenta-corriente/pagos/{pago_id}").status_code == 200

    recibo = admin_client.get(f"/api/recibos/{recibo_id}").json()
    assert recibo["anulado"] is True
    assert "elimino el pago" in recibo["anulado_motivo"]


# ── Venta: el origen que necesita el lector propio de Contalibra ─────────────

def test_el_recibo_de_una_venta_lee_las_ventas_de_contalibra(admin_client):
    """Las ventas de Contalibra viven en `sales` (LibraCommerce), no en la
    tabla `ventas` del schema core — que existe en esta misma base y está
    vacía. Si el cableado dejara el lector por defecto del motor, esto no
    fallaría con un error visible: devolvería un recibo sin datos."""
    c = _cliente(admin_client, "Compra al contado")
    venta = admin_client.post("/api/ventas", json={
        "fecha": HOY, "cliente_id": c["id"],
        "items": [{"nombre": "Mercaderia", "qty": 2, "precio": 250.0}],
        "pagos": [{"medio": "efectivo", "monto": 500.0}],
    }).json()

    recibo = admin_client.post(f"/api/recibos/venta/{venta['id']}").json()
    assert recibo["total"] == 500.0
    assert recibo["origen_tipo"] == "venta"
    assert recibo["cliente_razon"] == "Compra al contado"


def test_el_link_viejo_del_recibo_de_venta_sigue_andando(admin_client):
    """`Ventas.tsx` y `VentaDetalle.tsx` linkean esta URL: no se puede mover."""
    c = _cliente(admin_client, "Link viejo")
    venta = admin_client.post("/api/ventas", json={
        "fecha": HOY, "cliente_id": c["id"],
        "items": [{"nombre": "Mercaderia", "qty": 1, "precio": 300.0}],
        "pagos": [{"medio": "efectivo", "monto": 300.0}],
    }).json()

    resp = admin_client.get(f"/ventas/{venta['id']}/recibo")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "0001-00000001" in _texto_del_pdf(resp.content)


# ── El PDF ───────────────────────────────────────────────────────────────────

def test_el_pdf_del_recibo_sale_por_http_con_los_datos_del_cobro(admin_client):
    c = _deudor(admin_client, "Con PDF")
    recibo_id = admin_client.post(f"/api/cuenta-corriente/{c['id']}/pagar",
                                  json={"monto": 1000.0, "fecha": HOY,
                                        "medio_pago": "transferencia",
                                        "referencia": "transf 991"}).json()["recibo_id"]

    resp = admin_client.get(f"/api/recibos/{recibo_id}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    texto = _texto_del_pdf(resp.content)
    assert "0001-00000001" in texto
    assert "Con PDF" in texto
    assert "1.000,00" in texto
    assert "transf 991" in texto


def test_reimprimir_devuelve_el_mismo_papel(admin_client):
    c = _deudor(admin_client, "Reimprime")
    recibo_id = admin_client.post(f"/api/cuenta-corriente/{c['id']}/pagar",
                                  json={"monto": 1000.0, "fecha": HOY}).json()["recibo_id"]
    primero = admin_client.get(f"/api/recibos/{recibo_id}/pdf").content
    segundo = admin_client.get(f"/api/recibos/{recibo_id}/pdf").content
    assert _sin_la_hora_de_generacion(primero) == _sin_la_hora_de_generacion(segundo)

    # La normalizacion tiene que sacar la hora y NADA MAS: si se comiera el
    # cuerpo, el assert de arriba pasaria con dos recibos distintos.
    assert b"%PDF-" in _sin_la_hora_de_generacion(primero)
    assert "Reimprime" in _texto_del_pdf(_sin_la_hora_de_generacion(primero))
    assert b"/CreationDate (D:" not in _sin_la_hora_de_generacion(primero)


# ── Anulación ────────────────────────────────────────────────────────────────

def test_anular_marca_el_recibo_y_no_mueve_el_saldo(admin_client):
    """El recibo es el comprobante del cobro, no el cobro."""
    c = _deudor(admin_client, "Anula el papel")
    recibo_id = admin_client.post(f"/api/cuenta-corriente/{c['id']}/pagar",
                                  json={"monto": 1000.0, "fecha": HOY}).json()["recibo_id"]
    saldo_antes = admin_client.get(f"/api/cuenta-corriente/{c['id']}").json()["saldo"]

    resp = admin_client.post(f"/api/recibos/{recibo_id}/anular",
                             json={"motivo": "se imprimio mal"})
    assert resp.status_code == 200
    assert resp.json()["anulado"] is True

    saldo_despues = admin_client.get(f"/api/cuenta-corriente/{c['id']}").json()["saldo"]
    assert saldo_despues == saldo_antes


def test_el_anulado_se_puede_seguir_imprimiendo_y_lo_dice(admin_client):
    c = _deudor(admin_client, "Anulado imprimible")
    recibo_id = admin_client.post(f"/api/cuenta-corriente/{c['id']}/pagar",
                                  json={"monto": 1000.0, "fecha": HOY}).json()["recibo_id"]
    admin_client.post(f"/api/recibos/{recibo_id}/anular", json={"motivo": "duplicado"})

    resp = admin_client.get(f"/api/recibos/{recibo_id}/pdf")
    assert resp.status_code == 200
    texto = _texto_del_pdf(resp.content)
    assert "ANULADO" in texto
    assert "duplicado" in texto


def test_anular_dos_veces_avisa(admin_client):
    c = _deudor(admin_client, "Doble anulacion")
    recibo_id = admin_client.post(f"/api/cuenta-corriente/{c['id']}/pagar",
                                  json={"monto": 1000.0, "fecha": HOY}).json()["recibo_id"]
    admin_client.post(f"/api/recibos/{recibo_id}/anular", json={})
    assert admin_client.post(f"/api/recibos/{recibo_id}/anular", json={}).status_code == 409


def test_anular_es_solo_de_admin(client, admin_client):
    """El listado y el PDF los ve cualquiera; anular no."""
    c = _deudor(admin_client, "Solo admin")
    recibo_id = admin_client.post(f"/api/cuenta-corriente/{c['id']}/pagar",
                                  json={"monto": 1000.0, "fecha": HOY}).json()["recibo_id"]
    admin_client.post("/api/usuarios", json={
        "username": "cajero", "nombre": "Cajero", "email": "cajero@test.com",
        "password": "cajero-1234", "role": "operador",
    })
    admin_client.post("/api/logout")
    assert client.post("/api/login", json={"username": "cajero",
                                           "password": "cajero-1234"}).status_code == 200

    assert client.get(f"/api/recibos/{recibo_id}/pdf").status_code == 200
    assert client.post(f"/api/recibos/{recibo_id}/anular", json={}).status_code in (401, 403)


# ── Listado ──────────────────────────────────────────────────────────────────

def test_el_listado_filtra_por_texto_y_por_anulados(admin_client):
    a = _deudor(admin_client, "Ferreteria Luna")
    b = _deudor(admin_client, "Panaderia Sol")
    admin_client.post(f"/api/cuenta-corriente/{a['id']}/pagar", json={"monto": 1000.0, "fecha": HOY})
    recibo_b = admin_client.post(f"/api/cuenta-corriente/{b['id']}/pagar",
                                 json={"monto": 1000.0, "fecha": HOY}).json()["recibo_id"]
    admin_client.post(f"/api/recibos/{recibo_b}/anular", json={})

    solo_luna = admin_client.get("/api/recibos?q=Luna").json()
    assert [r["cliente_razon"] for r in solo_luna["recibos"]] == ["Ferreteria Luna"]

    vigentes = admin_client.get("/api/recibos?incluir_anulados=false").json()
    assert vigentes["total"] == 1
    assert admin_client.get("/api/recibos").json()["total"] == 2


def test_un_recibo_que_no_existe_da_404(admin_client):
    assert admin_client.get("/api/recibos/99999").status_code == 404
    assert admin_client.get("/api/recibos/99999/pdf").status_code == 404
    assert admin_client.post("/api/recibos/99999/anular", json={}).status_code == 404


def test_una_factura_sin_cobros_no_emite_recibo(admin_client):
    assert admin_client.post("/api/recibos/factura/99999").status_code == 409


# ── Factura: el link que arma libra-ui y el cobro en cuotas ──────────────────

def _factura(client, **extra):
    """Con ENV=development la numeración es local y el CAE simulado — el mismo
    camino que corre dev.contalibra (ver tests/test_facturas.py)."""
    payload = {
        "tipo": 11, "fecha": HOY, "client_name": "Consumidor Final",
        "condicion_venta": "Contado",
        "items": [{"description": "Servicio de prueba", "qty": 1, "unit_price": 1000.0}],
    }
    payload.update(extra)
    resp = client.post("/api/facturas", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data.get("factura", data)


def test_el_link_viejo_del_recibo_de_factura_sigue_andando(admin_client):
    """Lo arma `libra-ui/FacturaDetalle.tsx`, que es código compartido con
    Restolibra: esta URL no se puede mover. Lo que cambió es que ahora
    devuelve un documento numerado en vez de un PDF armado al vuelo."""
    fid = _factura(admin_client)["id"]
    admin_client.post(f"/api/facturas/{fid}/cobrar", json={
        "fecha": HOY, "pagos": [{"medio_id": "efectivo", "monto": 1000.0}]})

    resp = admin_client.get(f"/facturas/{fid}/recibo")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    texto = _texto_del_pdf(resp.content)
    assert "0001-00000001" in texto
    assert "Cancelacion" in texto


def test_una_factura_sin_cobrar_no_da_recibo_por_el_link_viejo(admin_client):
    fid = _factura(admin_client)["id"]
    assert admin_client.get(f"/facturas/{fid}/recibo").status_code == 404


def test_cobrar_una_factura_en_dos_veces_da_dos_recibos_distintos(admin_client):
    """El único origen que acumula: cada cobro merece su papel, y el segundo
    cubre sólo lo nuevo. Es lo que el modelo viejo no podía sostener — el
    segundo cobro le cambiaba el PDF al primer recibo."""
    fid = _factura(admin_client)["id"]
    admin_client.post(f"/api/facturas/{fid}/cobrar", json={
        "fecha": HOY, "pagos": [{"medio_id": "efectivo", "monto": 400.0}]})
    primero = admin_client.post(f"/api/recibos/factura/{fid}").json()

    admin_client.post(f"/api/facturas/{fid}/cobrar", json={
        "fecha": HOY, "pagos": [{"medio_id": "transferencia", "monto": 600.0}]})
    segundo = admin_client.post(f"/api/recibos/factura/{fid}").json()

    assert primero["id"] != segundo["id"]
    assert primero["total"] == 400.0
    assert segundo["total"] == 600.0
    assert primero["concepto"].startswith("Pago parcial")
    assert segundo["concepto"].startswith("Cancelacion")

    # Y el primero no se movió: es el papel que el cliente ya se llevó.
    assert admin_client.get(f"/api/recibos/{primero['id']}").json()["total"] == 400.0
