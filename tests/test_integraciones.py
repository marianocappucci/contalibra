"""Consultas que llegan desde otro producto de la familia, para facturar acá.

🔴 **Lo que hay que probar no es que la venta se cree.** Lo caro son las tres
formas de crearla mal, y las tres son silenciosas:

1. **Sin usuario**, porque el token de servicio no es uno. La venta entra, suma
   su movimiento de caja y queda **fuera de todo turno**: el cierre no la ve.
2. **Dos veces**, porque el emisor reintentó. Dos ventas y dos facturas por una
   consulta, y la única señal es que a fin de mes no cierre.
3. **Con el comprobante equivocado**, porque los datos fiscales del paciente se
   ignoraron y todo salió Consumidor Final.

Cada uno tiene su test y su control al lado.
"""
import pytest
from fastapi.testclient import TestClient
from libraauth.session_auth import SERVICE_TOKEN_ENV, SERVICE_TOKEN_HEADER

from app import database as db

TOKEN = "un-token-de-servicio-de-prueba"


def _consulta(**cambios) -> dict:
    cuerpo = {
        "sistema": "medlibra",
        "referencia": "turno-abc-123",
        "fecha": "2026-08-24",
        "descripcion": "Consulta",
        "importe": 2500.0,
        "medio_pago": "efectivo",
        "paciente": {"nombre": "Ana Gómez", "cuit": "", "condicion_iva": ""},
        "facturar": False,
    }
    cuerpo.update(cambios)
    # `pagos` y `medio_pago` son excluyentes: mandar los dos es un pedido
    # ambiguo y el endpoint lo rechaza. El default de este helper es la forma
    # vieja, así que pedir `pagos` saca la otra.
    if cuerpo.get("pagos"):
        cuerpo.pop("medio_pago", None)
    return cuerpo


@pytest.fixture
def configurado(admin_client: TestClient) -> TestClient:
    """Con el usuario de integraciones apuntando al admin de la instancia."""
    puesto = admin_client.put("/api/integraciones/config", json={"username": "admin"})
    assert puesto.status_code == 200, puesto.text
    return admin_client


def _mandar(client: TestClient, **cambios):
    return client.post("/api/integraciones/consultas", json=_consulta(**cambios))


# ── La configuración del usuario ───────────────────────────────────────────

def test_arranca_sin_usuario_configurado(admin_client: TestClient):
    assert admin_client.get("/api/integraciones/config").json() == {
        "usuario_integraciones": ""
    }


def test_no_se_puede_configurar_un_usuario_que_no_existe(admin_client: TestClient):
    """Configurar un username inexistente dejaría la integración *pareciendo*
    lista y fallando recién con la primera consulta."""
    rechazado = admin_client.put(
        "/api/integraciones/config", json={"username": "fantasma"},
    )
    assert rechazado.status_code == 422
    assert "fantasma" in rechazado.json()["detail"]


def test_vaciar_el_username_apaga_la_integracion(configurado: TestClient):
    configurado.put("/api/integraciones/config", json={"username": ""})
    apagado = _mandar(configurado)
    assert apagado.status_code == 409
    assert "usuario para integraciones" in apagado.json()["detail"]


# ── 1. Sin usuario, la venta no se crea ────────────────────────────────────

def test_sin_usuario_configurado_rechaza_en_vez_de_crear_la_venta(
    admin_client: TestClient,
):
    """🔴 **Falla cerrado.** Crear la venta sin `usuario_id` no rompe nada: entra,
    suma su movimiento de caja y queda fuera de todo turno. El descuadre se
    descubre a fin de mes."""
    rechazado = _mandar(admin_client)
    assert rechazado.status_code == 409
    assert db.get_all_ventas() == []


def test_con_usuario_configurado_la_venta_queda_a_su_nombre(configurado: TestClient):
    """🔴 El control, y lo que hace que la venta entre al turno de caja: el
    `usuario_id` no es una etiqueta de auditoría, es de dónde sale
    `get_turno_activo`."""
    creada = _mandar(configurado)
    assert creada.status_code == 200, creada.text
    venta = creada.json()["venta"]
    admin = db.get_usuario_by_username("admin")
    assert venta["usuario_id"] == admin["id"]
    assert venta["total"] == 2500.0
    assert venta["cliente_nombre"] == "Ana Gómez"


def test_la_venta_externa_entra_al_turno_de_caja_abierto(configurado: TestClient):
    """🔴 **Éste es el test que justifica todo el diseño.**

    La razón de que la instancia configure un usuario —en vez de dejar que el
    token de servicio cree la venta sin dueño— es exactamente ésta:
    `crear_venta_directa` engancha la venta al turno **a través del
    `usuario_id`**. Con `None` la venta entra igual, suma su movimiento de caja
    y queda huérfana de turno: el cierre no la ve y el descuadre aparece a fin
    de mes, sin nada que lo explique.
    """
    abierto = configurado.post("/api/turnos/abrir", json={"monto_inicial": 5000.0})
    assert abierto.status_code == 200, abierto.text
    turno_id = abierto.json()["id"]

    creada = _mandar(configurado)
    assert creada.json()["venta"]["turno_id"] == turno_id


def test_sin_turno_abierto_la_venta_entra_igual(configurado: TestClient):
    """🔴 El control por el otro lado: **no** se rechaza la consulta porque no
    haya turno. Un consultorio puede completar un turno fuera del horario de
    caja, y perder la venta sería peor que registrarla sin turno."""
    creada = _mandar(configurado)
    assert creada.status_code == 200
    assert creada.json()["venta"]["turno_id"] is None


def test_el_pedido_no_puede_elegir_a_quien_atribuirle_la_venta(
    configurado: TestClient,
):
    """🔴 Un `usuario_id` en el payload se ignora. Si se respetara, cualquiera
    con el token podría atribuirle ventas a cualquier usuario de la instancia."""
    creada = configurado.post(
        "/api/integraciones/consultas",
        json={**_consulta(), "usuario_id": 99999, "username": "otro"},
    )
    assert creada.status_code == 200, creada.text
    admin = db.get_usuario_by_username("admin")
    assert creada.json()["venta"]["usuario_id"] == admin["id"]


# ── 2. La idempotencia ─────────────────────────────────────────────────────

def test_la_misma_referencia_no_crea_una_segunda_venta(configurado: TestClient):
    """El emisor reintenta —un timeout, un deploy en el medio— y no puede
    terminar con dos ventas por una consulta."""
    primera = _mandar(configurado)
    segunda = _mandar(configurado)

    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert primera.json()["ya_existia"] is False
    assert segunda.json()["ya_existia"] is True
    assert segunda.json()["venta"]["id"] == primera.json()["venta"]["id"]
    assert len(db.get_all_ventas()) == 1


def test_otra_referencia_si_crea_otra_venta(configurado: TestClient):
    """🔴 El control. Sin esto, "devolver siempre la primera venta" haría pasar
    al test de arriba — y el consultorio facturaría una sola consulta por día."""
    _mandar(configurado, referencia="turno-abc-123")
    _mandar(configurado, referencia="turno-def-456")
    assert len(db.get_all_ventas()) == 2


def test_el_mismo_id_desde_otro_sistema_no_colisiona(configurado: TestClient):
    """La clave es `(sistema, referencia)`, no la referencia sola: dos productos
    pueden numerar sus turnos igual."""
    _mandar(configurado, sistema="medlibra", referencia="1")
    _mandar(configurado, sistema="gestiolibra", referencia="1")
    assert len(db.get_all_ventas()) == 2


def test_la_venta_queda_atada_a_su_referencia(configurado: TestClient):
    venta_id = _mandar(configurado).json()["venta"]["id"]
    origen = db.get_origen_de_venta(venta_id)
    assert origen["sistema"] == "medlibra"
    assert origen["referencia"] == "turno-abc-123"


# ── 3. El comprobante ──────────────────────────────────────────────────────

def test_sin_datos_fiscales_va_como_consumidor_final(configurado: TestClient):
    """Es el caso normal de un consultorio: no se crea cliente."""
    creada = _mandar(configurado)
    assert creada.json()["venta"]["cliente_id"] is None
    assert db.get_all_clients() == []


def test_con_cuit_se_crea_el_cliente_y_la_venta_va_a_su_nombre(
    configurado: TestClient,
):
    """Sin esto, un paciente Responsable Inscripto recibiría Factura B."""
    creada = _mandar(configurado, paciente={
        "nombre": "Clínica del Sur SRL",
        "cuit": "30711223344",
        "condicion_iva": "Responsable Inscripto",
    })
    cliente_id = creada.json()["venta"]["cliente_id"]
    assert cliente_id is not None
    cliente = db.get_client(cliente_id)
    assert cliente["cuit_dni"] == "30711223344"
    assert cliente["iva_condition"] == "Responsable Inscripto"


def test_un_cuit_que_ya_es_cliente_no_se_duplica(configurado: TestClient):
    """🔴 Se busca por CUIT y no por nombre: dos homónimos compartirían cuenta
    corriente y comprobantes, y el mismo paciente escrito distinto abriría un
    cliente nuevo cada vez."""
    paciente = {
        "nombre": "Clínica del Sur SRL",
        "cuit": "30711223344",
        "condicion_iva": "Responsable Inscripto",
    }
    primera = _mandar(configurado, referencia="t-1", paciente=paciente)
    # Mismo CUIT, el nombre escrito distinto.
    segunda = _mandar(
        configurado, referencia="t-2",
        paciente={**paciente, "nombre": "CLINICA DEL SUR S.R.L."},
    )
    assert primera.json()["venta"]["cliente_id"] == segunda.json()["venta"]["cliente_id"]
    assert len(db.get_all_clients()) == 1


# ── Una consulta con más de un pago ────────────────────────────────────────
#
# 🔴 **El caso que motiva todo esto es el turno señado.** MedLibra cobra la seña
# cuando se reserva y el saldo cuando se atiende, y pueden ser medios distintos.
# Mandando un solo `medio_pago`, 400 de seña por MercadoPago y 600 en efectivo
# entraban acá como **1000 en efectivo**: la venta cerraba por el total correcto
# y el reparto de la caja quedaba mal. El cierre no cuadra contra el arqueo y la
# diferencia no tiene de dónde salir.


def _pagos_de(venta: dict) -> dict:
    """`{medio: monto}` de la venta creada."""
    return {p["medio"]: p["monto"] for p in venta["pagos"]}


def test_una_sena_y_un_saldo_entran_como_DOS_pagos(configurado: TestClient):
    creada = _mandar(configurado, importe=1000.0, pagos=[
        {"medio": "mercadopago", "monto": 400.0, "referencia": "seña"},
        {"medio": "efectivo", "monto": 600.0},
    ])
    assert creada.status_code == 200, creada.text
    venta = creada.json()["venta"]
    assert _pagos_de(venta) == {"mercadopago": 400.0, "efectivo": 600.0}
    assert venta["total"] == 1000.0
    assert venta["estado"] == "cobrada"


def test_cada_pago_genera_su_movimiento_de_caja(configurado: TestClient):
    """🔴 **Éste es el test que mide el defecto real**, y no el de arriba.

    Que la venta guarde dos pagos no alcanza: lo que se descuadra es la **caja**,
    y el cierre la agrupa por el `medio_pago` de `caja_movimientos`. Si los dos
    movimientos salieran con el mismo medio —o si saliera uno solo por 1000— la
    venta se vería bien y el arqueo seguiría sin cuadrar.
    """
    abierto = configurado.post("/api/turnos/abrir", json={"monto_inicial": 0.0})
    assert abierto.status_code == 200, abierto.text

    _mandar(configurado, importe=1000.0, pagos=[
        {"medio": "mercadopago", "monto": 400.0},
        {"medio": "efectivo", "monto": 600.0},
    ])

    cierre = configurado.get(f"/api/turnos/{abierto.json()['id']}")
    assert cierre.status_code == 200, cierre.text
    por_medio = cierre.json()["resumen"]["pagos_por_medio"]
    assert por_medio.get("efectivo") == 600.0, por_medio
    assert por_medio.get("mercadopago") == 400.0, por_medio


def test_la_forma_vieja_de_un_solo_medio_sigue_andando(configurado: TestClient):
    """🔴 El control de compatibilidad. Un emisor que todavía no se actualizó
    manda `medio_pago`, y romperlo dejaría sus consultas rebotando con 422 —
    visibles en su pantalla de facturación externa, pero sin facturar."""
    creada = _mandar(configurado, medio_pago="transferencia")
    assert creada.status_code == 200, creada.text
    assert _pagos_de(creada.json()["venta"]) == {"transferencia": 2500.0}


def test_mandar_las_dos_formas_a_la_vez_se_rechaza(configurado: TestClient):
    """Es un pedido ambiguo: no se sabe si el importe entero va por el medio
    suelto o si los pagos son el detalle. Elegir uno sería adivinar."""
    ambiguo = configurado.post("/api/integraciones/consultas", json={
        **_consulta(), "medio_pago": "efectivo",
        "pagos": [{"medio": "efectivo", "monto": 2500.0}],
    })
    assert ambiguo.status_code == 422
    assert db.get_all_ventas() == []


def test_sin_ninguna_de_las_dos_se_rechaza(configurado: TestClient):
    """El control por el otro lado: sin esto, "aceptar si falta una" dejaría
    entrar un pedido sin medio de pago y la venta se marcaría cobrada igual."""
    cuerpo = _consulta()
    cuerpo.pop("medio_pago")
    sin_medio = configurado.post("/api/integraciones/consultas", json=cuerpo)
    assert sin_medio.status_code == 422
    assert db.get_all_ventas() == []


# ── Los pagos tienen que cerrar ────────────────────────────────────────────

def test_pagos_que_no_suman_el_importe_se_rechazan(configurado: TestClient):
    """🔴 **Falla cerrado, y por una razón concreta.**

    Este endpoint marca la venta `cobrada` sin mirar lo pagado — a diferencia de
    `POST /api/ventas`, que deriva el estado. Con pagos que no cierran, eso es
    una venta que dice estar cobrada y no lo está, y el descuadre aparece a fin
    de mes sin nada que lo explique.
    """
    corto = _mandar(configurado, importe=1000.0, pagos=[
        {"medio": "efectivo", "monto": 600.0},
    ])
    assert corto.status_code == 422
    assert "600" in corto.text and "1000" in corto.text, corto.text
    assert db.get_all_ventas() == [], "no se crea la venta si el pedido no cierra"


def test_pagos_que_suman_de_mas_tambien_se_rechazan(configurado: TestClient):
    """El otro lado del mismo error: cobrar 1200 por una consulta de 1000 mete
    200 en la caja que ninguna venta explica."""
    largo = _mandar(configurado, importe=1000.0, pagos=[
        {"medio": "efectivo", "monto": 600.0},
        {"medio": "mercadopago", "monto": 600.0},
    ])
    assert largo.status_code == 422
    assert db.get_all_ventas() == []


def test_una_suma_con_centavos_de_float_no_se_rechaza_por_eso(configurado: TestClient):
    """🔴 El control que evita rechazar un pedido correcto. Los dos lados vienen
    de floats, así que la suma puede no dar el total exacto en binario: comparar
    sin redondear haría rebotar un reparto legítimo, y la consulta terminaría
    sin facturar por un problema de representación.

    ⚠️ **Los números importan.** Acá había `33.33 + 33.33 + 33.34` contra
    `100.0`, que en binario da **exactamente** `100.0` — el test pasaba con y sin
    el redondeo, o sea que no medía nada. Lo delató la mutación: sacar el
    `round()` no lo ponía en rojo. Éstos sí: `198.99 + 172.47` da
    `371.46000000000004`.
    """
    assert 198.99 + 172.47 != 371.46, "el caso dejó de romper: buscar otro"
    partido = _mandar(configurado, importe=371.46, pagos=[
        {"medio": "efectivo", "monto": 198.99},
        {"medio": "transferencia", "monto": 172.47},
    ])
    assert partido.status_code == 200, partido.text


# ── El vocabulario de medios ───────────────────────────────────────────────

def test_un_medio_que_no_existe_se_rechaza(configurado: TestClient):
    """🔴 Hasta el 2026-08-24 acá entraba **cualquier string**: `PagoPayload.
    medio` del mostrador es `str` pelado y `add_venta_pago()` tampoco mira. Un
    medio inventado creaba su movimiento de caja y salía en el cierre como un
    bucket suelto con el nombre crudo — la plata bien contada y el reparto mal.

    Es exactamente cómo MedLibra venía mandando `tarjeta`, que no existía en
    ninguna lista de esta casa."""
    inventado = _mandar(configurado, pagos=[
        {"medio": "criptomonedas", "monto": 2500.0},
    ])
    assert inventado.status_code == 422
    assert "criptomonedas" in inventado.text
    assert db.get_all_ventas() == []


def test_la_grafia_vieja_tampoco_se_acepta_al_escribir(configurado: TestClient):
    """`tarjeta` se **lee** —hay ventas viejas con ese medio— pero no se
    escribe. Es la mitad que hace que la normalización avance en vez de
    quedarse: si se aceptara, MedLibra nunca migraría a `tarjeta_debito`."""
    vieja = _mandar(configurado, pagos=[{"medio": "tarjeta", "monto": 2500.0}])
    assert vieja.status_code == 422


def test_la_tarjeta_partida_si_entra(configurado: TestClient):
    """🔴 El control: sin esto, "rechazar todo lo que diga tarjeta" pasaría el
    test de arriba y el medio nuevo no serviría para nada."""
    creada = _mandar(configurado, pagos=[
        {"medio": "tarjeta_debito", "monto": 2500.0},
    ])
    assert creada.status_code == 200, creada.text
    assert _pagos_de(creada.json()["venta"]) == {"tarjeta_debito": 2500.0}


# ── La alícuota que trae el emisor ─────────────────────────────────────────
#
# 🔴 **En salud la mayoría de las prestaciones están EXENTAS**, y esa
# configuración es del producto que las presta (MedLibra la guarda por
# prestación), no del negocio que factura. Sin honrarla, una consulta exenta se
# declaraba al 21% **en silencio**: acá no hay forma de saber que lo era.


@pytest.fixture
def responsable_inscripto(configurado: TestClient) -> TestClient:
    """El emisor como Responsable Inscripto.

    🔴 **Sin esto los tests de alícuota pasan por la razón equivocada.** El
    default del config es *Monotributista*, que emite siempre **tipo C** — y un
    C no discrimina IVA, así que `iva_amount` da 0 con o sin el cambio que estos
    tests dicen medir. Se descubrió porque el control (*sin alícuota declarada
    corresponde el 21%*) se puso en rojo mientras el caso principal pasaba en
    verde: el par delató lo que cada uno por separado no podía.
    """
    puesto = configurado.put("/api/config/empresa", json={
        "empresa_nombre": "Consultorio Norte",
        "empresa_iva_condition": "Responsable Inscripto",
    })
    assert puesto.status_code == 200, puesto.text
    return configurado


def test_la_alicuota_que_manda_el_emisor_se_respeta(responsable_inscripto: TestClient):
    """Exenta: el total va entero al subtotal y el IVA queda en 0."""
    creada = _mandar(responsable_inscripto, facturar=True, iva_rate=0)
    assert creada.status_code == 200, creada.text
    factura = creada.json()["factura"]
    assert factura["total"] == 2500.0
    assert factura["iva_amount"] == 0.0
    assert factura["subtotal"] == 2500.0


def test_sin_alicuota_declarada_manda_el_default_de_esta_casa(
    responsable_inscripto: TestClient,
):
    """🔴 El control. Sin esto, "poner siempre 0" pasaría el test de arriba — y
    todas las ventas externas saldrían exentas, que es el error inverso y peor:
    IVA no declarado."""
    creada = _mandar(responsable_inscripto, facturar=True)
    factura = creada.json()["factura"]
    assert factura["total"] == 2500.0
    assert factura["iva_amount"] > 0, "sin alícuota declarada corresponde el 21%"


def test_la_alicuota_sobrevive_a_facturar_despues(responsable_inscripto: TestClient):
    """🔴 Se guarda con la venta, no sólo se pasa en la llamada.

    Una venta que entró sin facturar —o cuyo CAE falló— se factura después:
    desde la pantalla de Ventas, o reintentando. Si la alícuota viviera sólo en
    el pedido original, esos caminos volverían al default y la consulta exenta
    saldría al 21% sin que nada avise."""
    creada = _mandar(responsable_inscripto, facturar=False, iva_rate=0)
    venta_id = creada.json()["venta"]["id"]
    assert creada.json()["factura"] is None

    facturada = responsable_inscripto.post(f"/api/ventas/{venta_id}/facturar")
    assert facturada.status_code == 200, facturada.text
    assert facturada.json()["factura"]["iva_amount"] == 0.0


def test_un_porcentaje_en_vez_de_una_fraccion_rebota(responsable_inscripto: TestClient):
    """🔴 `21` queriendo decir 21% facturaría al **2100%**.

    Y no se notaría: el total lo pone la venta, así que el comprobante sale con
    un neto absurdo y un CAE real encima — que no se borra, se anula con nota de
    crédito. Falla cerrado con 422 antes de crear nada."""
    rechazado = _mandar(responsable_inscripto, facturar=True, iva_rate=21)
    assert rechazado.status_code == 422
    assert db.get_all_ventas() == [], "no se crea la venta si el pedido no valida"


def test_una_alicuota_valida_del_borde_entra(responsable_inscripto: TestClient):
    """🔴 El control: con `le=1` mal puesto (un `lt=1`, o un `le=0.5`) el test de
    arriba pasaría igual y el 100% quedaría rechazado sin motivo."""
    aceptado = _mandar(responsable_inscripto, facturar=False, iva_rate=1)
    assert aceptado.status_code == 200, aceptado.text


def test_una_venta_del_mostrador_no_se_ve_afectada(responsable_inscripto: TestClient):
    """🔴 El control por el otro lado: `get_alicuota_externa` devuelve `None`
    para una venta que no vino de afuera, así que el mostrador sigue con el
    default de siempre."""
    venta = responsable_inscripto.post("/api/ventas", json={
        "fecha": "2026-08-24",
        "items": [{"nombre": "Producto", "qty": 1, "precio": 2500.0}],
        "pagos": [{"medio": "efectivo", "monto": 2500.0}],
    })
    assert venta.status_code == 200, venta.text
    facturada = responsable_inscripto.post(f"/api/ventas/{venta.json()['id']}/facturar")
    assert facturada.status_code == 200, facturada.text
    assert facturada.json()["factura"]["iva_amount"] > 0


# ── La facturación ─────────────────────────────────────────────────────────

def test_con_facturar_emite_el_comprobante(configurado: TestClient):
    """La suite corre con `ENV=development`, así que ARCA devuelve un CAE
    simulado por el mismo camino que dev.contalibra."""
    creada = _mandar(configurado, facturar=True)
    assert creada.status_code == 200, creada.text
    factura = creada.json()["factura"]
    assert factura is not None
    assert factura["total"] == 2500.0
    assert factura["cae"]


def test_reintentar_una_consulta_ya_facturada_no_emite_otra(configurado: TestClient):
    """🔴 Dos facturas por una consulta es el daño que no se puede deshacer:
    un CAE emitido no se borra, se anula con una nota de crédito."""
    primera = _mandar(configurado, facturar=True)
    segunda = _mandar(configurado, facturar=True)
    assert segunda.json()["ya_existia"] is True
    assert segunda.json()["factura"]["id"] == primera.json()["factura"]["id"]
    assert len(db.get_all_facturas()) == 1


def test_sin_facturar_queda_la_venta_cobrada_y_sin_comprobante(
    configurado: TestClient,
):
    creada = _mandar(configurado, facturar=False)
    venta = creada.json()["venta"]
    assert creada.json()["factura"] is None
    assert venta["factura_id"] is None
    # `estado` es el legible que arma `_venta_dict`; el crudo es `status`.
    assert venta["estado"] == "cobrada"
    # Y la plata entró igual: la venta sin comprobante no es una venta sin cobrar.
    assert venta["pagos"][0]["monto"] == 2500.0


# ── El token de servicio ───────────────────────────────────────────────────

def test_el_token_de_servicio_abre_consultas(client: TestClient, monkeypatch):
    """Es lo que le permite al producto emisor mandar sin ser usuario de esta
    instancia. Se configura primero como admin, porque `/config` NO lo acepta."""
    resp = client.post("/api/login", json={
        "username": "admin", "password": __import__("os").environ["ADMIN_PASSWORD"],
    })
    assert resp.status_code == 200
    client.put("/api/integraciones/config", json={"username": "admin"})
    client.post("/api/logout")

    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    creada = client.post(
        "/api/integraciones/consultas", json=_consulta(),
        headers={SERVICE_TOKEN_HEADER: TOKEN},
    )
    assert creada.status_code == 200, creada.text
    assert len(db.get_all_ventas()) == 1


def test_sin_token_ni_sesion_no_entra(client: TestClient, monkeypatch):
    """🔴 El control del de arriba: sin esto, "el endpoint está abierto" pasaría
    igual."""
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    sin_nada = client.post("/api/integraciones/consultas", json=_consulta())
    assert sin_nada.status_code in (401, 403)

    token_malo = client.post(
        "/api/integraciones/consultas", json=_consulta(),
        headers={SERVICE_TOKEN_HEADER: "otro-token"},
    )
    assert token_malo.status_code in (401, 403)


def test_el_token_de_servicio_NO_abre_la_configuracion(
    client: TestClient, monkeypatch,
):
    """🔴 Quién recibe las ventas externas lo decide el dueño de la caja, no
    quien tiene el token. Si el token pudiera reconfigurarlo, el permiso que se
    amplió para mandar consultas serviría para redirigir la caja."""
    monkeypatch.setenv(SERVICE_TOKEN_ENV, TOKEN)
    cabeceras = {SERVICE_TOKEN_HEADER: TOKEN}
    assert client.get("/api/integraciones/config", headers=cabeceras).status_code in (401, 403)
    assert client.put(
        "/api/integraciones/config", json={"username": "admin"}, headers=cabeceras,
    ).status_code in (401, 403)
