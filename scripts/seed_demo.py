#!/usr/bin/env python3
"""Carga los datos de la demo pública de Contalibra — ítem 8 de los pendientes
transversales de Libra.

**Para qué.** Una demo vacía no muestra nada: quien entra ve pantallas en blanco
y se va. Este script deja la instancia con una distribuidora andando, para que
las pantallas se puedan mirar.

**Por la API y no por SQL**, a propósito: así los datos pasan por las mismas
validaciones y los mismos servicios que usa la pantalla. Un seed por SQL puede
crear estados que la aplicación nunca produciría —un presupuesto aceptado sin
su remito, por ejemplo— y entonces lo que se muestra no es el producto.

**No cubre sólo el caso feliz.** Deja los estados que las pantallas distinguen:
presupuestos en borrador, enviados, aceptados y rechazados; productos con stock
bajo el mínimo y uno en cero; una lista de precios además de la de referencia;
y clientes con las distintas condiciones frente al IVA, que es lo que decide el
tipo de comprobante.

🔴 **No emite facturas.** El módulo de facturación habla con ARCA de verdad; una
demo pública no puede pedir CAE contra el padrón por cada visita. Los
presupuestos y remitos sí se emiten: son documentos internos.

**Es idempotente**: si el registro ya existe no lo duplica. El cron de reset lo
corre después de recrear la base, pero correrlo dos veces no rompe nada.

> 🔴 **Nunca contra la instancia de un cliente.** Se planta si el host no es de
> dev, demo, prueba o local — ver `url_no_productiva`. Contalibra factura con
> clientes reales: acá los datos inventados entre los reales no se distinguen
> después.

Uso:
    python scripts/seed_demo.py --url https://demo.contalibra.com.ar \\
        --usuario admin --password ...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from http.cookiejar import CookieJar
from urllib.parse import urlparse

HOY = date.today()

#: Los subdominios que NO son de un cliente. Se compara el host entero o su
#: primera etiqueta, **no como substring de la URL**: con substrings, un cliente
#: llamado `demoliciones.contalibra.com.ar` pasaría la guarda.
_HOSTS_NO_PRODUCTIVOS = ("dev", "demo", "prueba", "localhost", "127.0.0.1")


def url_no_productiva(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    return host in _HOSTS_NO_PRODUCTIVOS or host.split(".")[0] in _HOSTS_NO_PRODUCTIVOS


class Api:
    def __init__(self, base: str):
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar())
        )

    def _pedir(self, metodo: str, ruta: str, cuerpo=None):
        datos = json.dumps(cuerpo, default=str).encode() if cuerpo is not None else None
        req = urllib.request.Request(
            f"{self.base}{ruta}", data=datos, method=metodo,
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.opener.open(req, timeout=30) as r:
                crudo = r.read()
                return json.loads(crudo) if crudo else None
        except urllib.error.HTTPError as e:
            detalle = e.read().decode(errors="replace")[:300]
            raise RuntimeError(f"{metodo} {ruta} -> {e.code}: {detalle}") from None

    def get(self, ruta):
        return self._pedir("GET", ruta)

    def post(self, ruta, cuerpo=None):
        return self._pedir("POST", ruta, cuerpo)

    def put(self, ruta, cuerpo=None):
        return self._pedir("PUT", ruta, cuerpo)


def _lista(datos):
    """Los listados de este producto a veces vienen envueltos
    (`{"items": [...]}`, `{"clientes": [...]}`). Devuelve siempre la lista."""
    if datos is None:
        return []
    if isinstance(datos, list):
        return datos
    return next((v for v in datos.values() if isinstance(v, list)), [])


def obtener_o_crear(api: Api, ruta: str, clave: str, valor, cuerpo: dict):
    """Crea el registro si no está. Devuelve `(registro, es_nuevo)`."""
    for existente in _lista(api.get(ruta)):
        if existente.get(clave) == valor:
            return existente, False
    return api.post(ruta, cuerpo), True


# ── El negocio ────────────────────────────────────────────────────────────
#
# Una distribuidora de insumos de oficina. Se eligió un rubro donde conviven
# productos y servicios —que es la distinción que este producto hace en el
# catálogo— y donde el presupuesto que se convierte en remito es el flujo
# natural.

CATEGORIAS = ["Papelería", "Informática", "Servicios"]

#: (nombre, código, categoría, tipo, precio venta, costo, stock mínimo)
PRODUCTOS = [
    ("Resma A4 75 g", "PAP-001", "Papelería", "producto", 8500, 6200, 20),
    ("Cuaderno tapa dura", "PAP-002", "Papelería", "producto", 4200, 2900, 15),
    ("Bolígrafo azul x50", "PAP-003", "Papelería", "producto", 12000, 8500, 10),
    ("Toner compatible HP", "INF-001", "Informática", "producto", 45000, 32000, 5),
    ("Mouse inalámbrico", "INF-002", "Informática", "producto", 18000, 12500, 8),
    ("Teclado USB", "INF-003", "Informática", "producto", 22000, 15000, 8),
    ("Cable HDMI 2 m", "INF-004", "Informática", "producto", 9500, 6000, 12),
    # Servicios: sin stock, y es correcto que no lo tengan.
    ("Instalación de impresora", "SRV-001", "Servicios", "servicio", 25000, 0, 0),
    ("Mantenimiento mensual", "SRV-002", "Servicios", "servicio", 85000, 0, 0),
]

#: Stock inicial. **No todos abastecidos**: uno en cero y dos por debajo del
#: mínimo, porque la pantalla de stock existe justamente para mostrar eso.
STOCK = {
    "PAP-001": 120,
    "PAP-002": 45,
    "PAP-003": 8,      # bajo el mínimo (10)
    "INF-001": 0,      # sin stock
    "INF-002": 24,
    "INF-003": 3,      # bajo el mínimo (8)
    "INF-004": 30,
}

#: Las cuatro condiciones frente al IVA que decide el tipo de comprobante.
#: Con todos los clientes iguales, esa parte del producto no se ve.
CLIENTES = [
    {"name": "Estudio Contable Bianchi", "cuit_dni": "30-71456789-1",
     "iva_condition": "Responsable Inscripto", "email": "admin@example.com.ar",
     "phone": "11 4383-5500", "address": "Lavalle 1200, CABA"},
    {"name": "Colegio Santa Rita", "cuit_dni": "30-71222444-6",
     "iva_condition": "IVA Exento", "email": "compras@example.com.ar",
     "phone": "11 4671-2200", "address": "Av. Directorio 3400, CABA"},
    {"name": "Verónica Aguilar", "cuit_dni": "27-28456123-9",
     "iva_condition": "Monotributista", "phone": "11 5544-8899"},
    {"name": "Consumidor final", "iva_condition": "Consumidor Final"},
    {"name": "Distribuidora del Oeste SRL", "cuit_dni": "30-70998877-5",
     "iva_condition": "Responsable Inscripto", "phone": "11 4629-3300",
     "address": "Ruta 8 km 32, Moreno"},
]

PROVEEDORES = [
    {"nombre": "Papelera Central SA", "cuit_dni": "30-70111333-2",
     "iva_condition": "Responsable Inscripto", "phone": "11 4300-7788"},
    {"nombre": "Insumos Tecnológicos SRL", "cuit_dni": "30-70555777-4",
     "iva_condition": "Responsable Inscripto", "email": "ventas@example.com.ar"},
]


def sembrar(api: Api) -> None:
    hechos = {}

    def contar(clave: str, nuevo: bool):
        creados, existentes = hechos.get(clave, (0, 0))
        hechos[clave] = (creados + int(nuevo), existentes + int(not nuevo))

    print("Categorías…")
    for nombre in CATEGORIAS:
        _, nuevo = obtener_o_crear(api, "/api/productos/categorias", "nombre",
                                   nombre, {"nombre": nombre})
        contar("categorías", nuevo)

    print("Productos…")
    productos = {}
    for nombre, codigo, categoria, tipo, venta, costo, minimo in PRODUCTOS:
        registro, nuevo = obtener_o_crear(api, "/api/productos", "codigo", codigo, {
            "nombre": nombre, "codigo": codigo, "categoria": categoria,
            "tipo": tipo, "precio_venta": venta, "precio_costo": costo,
            "stock_minimo": minimo,
        })
        productos[codigo] = registro["id"]
        contar("productos", nuevo)

    print("Clientes…")
    clientes = {}
    for c in CLIENTES:
        registro, nuevo = obtener_o_crear(api, "/api/clientes", "name", c["name"], c)
        clientes[c["name"]] = registro["id"]
        contar("clientes", nuevo)

    print("Proveedores…")
    for p in PROVEEDORES:
        _, nuevo = obtener_o_crear(api, "/api/proveedores", "nombre", p["nombre"], p)
        contar("proveedores", nuevo)

    print("Stock…")
    for codigo, cantidad in STOCK.items():
        if cantidad == 0:
            # Sin ajuste: queda en cero, que es el estado que la pantalla de
            # faltantes tiene que mostrar.
            continue
        # `modo: absoluto` es idempotente por definición: fija la existencia,
        # no la suma. Correr el seed dos veces deja el mismo número.
        api.post(f"/api/stock/{productos[codigo]}/ajuste", {
            "modo": "absoluto", "cantidad": cantidad,
            "referencia": "Carga inicial de la demo",
        })
        contar("stock", True)

    print("Lista de precios…")
    _, nuevo = obtener_o_crear(api, "/api/listas-precio", "nombre", "Mayorista", {
        "nombre": "Mayorista",
        "descripcion": "15% de descuento sobre la lista de referencia",
    })
    contar("listas", nuevo)

    print("Presupuestos…")
    _sembrar_presupuestos(api, clientes, contar)

    print("Operación del día (turno, ventas, facturas, caja, cobranzas)…")
    _sembrar_operacion(api, clientes, productos, contar)

    print("Tesorería…")
    _sembrar_tesoreria(api, contar)

    print("Bandeja de MercadoPago…")
    _sembrar_bandeja_mp(api, contar)

    # 🔴 El stock se vuelve a fijar DESPUÉS de las ventas, y no es redundante:
    # las ventas descuentan, así que sin esto la primera corrida terminaba en
    # 117 unidades y la segunda —que saltea las ventas ya creadas— en 120. El
    # seed dejaba de ser idempotente y el reset diario mostraba números
    # distintos según cuántas veces hubiera corrido. Lo agarró
    # `test_la_segunda_corrida_no_cambia_el_stock`.
    #
    # Va en modo `absoluto`, que fija la existencia en vez de sumarla: correrlo
    # de nuevo no cambia nada.
    # 🔴 Acá NO se saltea el cero, a diferencia de la carga inicial. Allá 0
    # significa "no toques, dejalo sin abastecer"; acá significa "volvé a
    # cero". Salteándolo, cada corrida empujaba ese ítem un poco más abajo
    # —negativo— y el seed dejaba de ser idempotente.
    for codigo, cantidad in STOCK.items():
        api.post(f"/api/stock/{productos[codigo]}/ajuste", {
            "modo": "absoluto", "cantidad": cantidad,
            "referencia": "Ajuste de inventario",
        })

    # El logo del negocio, para que los comprobantes salgan como los de
    # un cliente y no con un hueco arriba.
    _cargar_logo(api, "Insumos del Plata SRL", "I", (37, 99, 235), contar)

    print()
    for clave, (creados, existentes) in sorted(hechos.items()):
        print(f"  {clave:<13} {creados} creados, {existentes} ya estaban")


def _sembrar_bandeja_mp(api: Api, contar) -> None:
    """Cobros de MercadoPago esperando factura.

    🔴 **Por qué hace falta una ruta aparte y no alcanza con la API normal.**
    La bandeja se llena **sincronizando contra MercadoPago de verdad**:
    `/api/mp-bandeja/sincronizar` exige el Access Token de la cuenta y sale a
    la red. Una demo pública no tiene cuenta de MP ni puede tenerla, así que
    esta pantalla era la única que seguía abriéndose vacía — y es de las que
    mejor muestran el producto, porque es el cobro que entra y se factura solo.
    Por eso el producto expone `/api/mp-bandeja/demo/sembrar`, que **existe
    sólo con `DEMO_MODE`**.

    Se siembran las **dos** solapas: cobros y transferencias bancarias
    entrantes. Con una sola llena la pantalla queda a medias.

    Y se dejan **pendientes**, no facturados: lo que hay que mostrar es la
    acción disponible —el botón de facturar— y no un historial cerrado. Uno
    de los cobros va sin CUIT a propósito, que es el caso en el que el
    producto pide completar los datos antes de facturar.
    """
    bandeja = api.get("/api/mp-bandeja") or {}
    if bandeja.get("pendientes") or bandeja.get("transferencias"):
        contar("mp_bandeja", False)
        return

    items = [
        {"mp_payment_id": "demo-105544321", "monto": 148000,
         "payer_name": "Distribuidora del Oeste SRL",
         "payer_email": "pagos@distribuidoradeloeste.com.ar",
         "payer_id_number": "30709988775", "payment_type": "account_money",
         "payment_method": "account_money",
         "descripcion": "Pago de factura de servicios", "clase": "pago"},
        {"mp_payment_id": "demo-105544322", "monto": 62500,
         "payer_name": "Verónica Aguilar", "payer_email": "veronica.aguilar@example.com.ar",
         "payer_id_number": "27284561239", "payment_type": "credit_card",
         "payment_method": "visa", "descripcion": "Cobro con QR en mostrador",
         "clase": "pago"},
        # Sin CUIT: es el caso en que el producto pide completar los datos del
        # pagador antes de poder emitir el comprobante.
        {"mp_payment_id": "demo-105544323", "monto": 19800,
         "payer_name": "Consumidor final", "payer_email": "",
         "payer_id_number": "", "payment_type": "debit_card",
         "payment_method": "maestro", "descripcion": "Venta de mostrador",
         "clase": "pago"},
        {"mp_payment_id": "demo-880011", "monto": 315000,
         "payer_name": "Estudio Contable Márquez",
         "payer_email": "administracion@estudiomarquez.com.ar",
         "payer_id_number": "30715544663", "payment_type": "bank_transfer",
         "payment_method": "cvu", "descripcion": "Transferencia recibida",
         "clase": "transferencia"},
    ]
    try:
        r = api.post("/api/mp-bandeja/demo/sembrar", items)
        for _ in range(int((r or {}).get("creados", 0))):
            contar("mp_bandeja", True)
    except RuntimeError as e:
        # Fuera de una demo la ruta no existe: es lo esperado, no un error.
        print(f"  (bandeja de MP: {e})")


def _sembrar_tesoreria(api: Api, contar) -> None:
    """Cuentas de tesorería, sus movimientos y una transferencia entre las dos.

    Tesorería es la plata que **no** está en la caja del día: la cuenta del
    banco, el efectivo guardado. Por eso son cuentas propias y no movimientos
    de caja — y por eso la transferencia entre las dos es el ejemplo que hace
    entender la pantalla: mostrar sólo ingresos deja la mitad sin verse.

    Portado de [[restolibra]], que comparte el módulo: acá la pantalla se abría
    con `{"cuentas": [], "movimientos": []}`, medido contra la demo.
    """
    resumen = api.get("/api/tesoreria") or {}
    if resumen.get("cuentas"):
        contar("tesoreria", False)
        return

    cuentas = {}
    for nombre, tipo, banco, saldo in (
        ("Cuenta corriente Banco Galicia", "banco", "Banco Galicia", 1200000),
        ("Efectivo en caja fuerte", "efectivo", "", 180000),
    ):
        try:
            creada = api.post("/api/tesoreria/cuentas", {
                "nombre": nombre, "tipo": tipo, "banco": banco,
                "saldo_inicial": saldo,
                "descripcion": "Cuenta de ejemplo de la demo",
            })
            cuentas[nombre] = creada.get("id") or creada.get("cuenta", {}).get("id")
            contar("tesoreria", True)
        except RuntimeError as e:
            print(f"  -- cuenta {nombre}: {e}")

    banco = cuentas.get("Cuenta corriente Banco Galicia")
    caja_fuerte = cuentas.get("Efectivo en caja fuerte")

    if banco:
        for tipo, concepto, monto in (
            ("ingreso", "Acreditación de cobranzas del mes", 640000),
            ("egreso", "Pago de sueldos", 480000),
        ):
            try:
                api.post(f"/api/tesoreria/cuentas/{banco}/movimiento", {
                    "fecha": HOY.isoformat(), "tipo": tipo,
                    "monto": monto, "concepto": concepto,
                    "referencia": "Movimiento de ejemplo",
                })
                contar("tesoreria_mov", True)
            except RuntimeError as e:
                print(f"  -- movimiento de tesorería: {e}")

    if banco and caja_fuerte:
        try:
            api.post("/api/tesoreria/transferencia", {
                "cuenta_origen_id": caja_fuerte, "cuenta_destino_id": banco,
                "monto": 90000, "fecha": HOY.isoformat(),
                "concepto": "Depósito del efectivo de la semana",
            })
            contar("transferencia", True)
        except RuntimeError as e:
            print(f"  -- transferencia: {e}")


def _sembrar_presupuestos(api: Api, clientes: dict, contar) -> None:
    """Presupuestos en los cuatro estados que la pantalla distingue.

    🔴 **No se emiten facturas.** El módulo de facturación habla con ARCA de
    verdad: pedir CAE contra el padrón por cada visita a una demo pública no es
    algo que se pueda dejar corriendo. Los presupuestos y remitos sí, que son
    documentos internos y no fiscales.
    """
    if len(_lista(api.get("/api/presupuestos"))) >= 4:
        contar("presupuestos", False)
        print("  (ya hay presupuestos cargados)")
        return

    # (cliente, días atrás, items, estado final)
    PLAN = [
        ("Estudio Contable Bianchi", 12, [
            ("Resma A4 75 g", 20, 8500),
            ("Toner compatible HP", 2, 45000),
        ], "aceptado"),
        ("Colegio Santa Rita", 8, [
            ("Cuaderno tapa dura", 60, 4200),
            ("Bolígrafo azul x50", 4, 12000),
        ], "enviado"),
        ("Distribuidora del Oeste SRL", 5, [
            ("Mouse inalámbrico", 10, 18000),
            ("Teclado USB", 10, 22000),
            ("Cable HDMI 2 m", 5, 9500),
        ], "rechazado"),
        ("Verónica Aguilar", 2, [
            ("Instalación de impresora", 1, 25000),
        ], "enviado"),
        # En borrador: el estado inicial, y el que la pantalla usa para saber
        # qué se puede seguir editando.
        ("Estudio Contable Bianchi", 0, [
            ("Mantenimiento mensual", 1, 85000),
        ], None),
    ]

    for cliente, dias, items, estado in PLAN:
        fecha = HOY - timedelta(days=dias)
        try:
            presupuesto = api.post("/api/presupuestos", {
                "date": fecha.isoformat(),
                "valid_until": (fecha + timedelta(days=30)).isoformat(),
                "client_id": clientes[cliente],
                "items": [{"description": d, "qty": c, "unit_price": p}
                          for d, c, p in items],
                "observations": "Presupuesto de ejemplo de la demo.",
            })
        except RuntimeError as e:
            print(f"  -- presupuesto de {cliente}: {e}")
            continue
        contar("presupuestos", True)
        if estado:
            try:
                api.post(f"/api/presupuestos/{presupuesto['id']}/estado", {
                    "estado": estado,
                    # El aceptado genera su remito, que es el flujo natural del
                    # producto: un presupuesto aceptado sin remito se lee como
                    # algo a medio hacer.
                    "convertir_remito": estado == "aceptado",
                })
            except RuntimeError as e:
                print(f"  -- estado {estado}: {e}")


def _sesion_del_visitante(api):
    """Una sesión con el usuario de la demo, si la instancia es una demo.

    Existe para lo que el producto ordena **por usuario**: un turno de caja
    abierto por el admin no aparece en la pantalla del visitante, aunque esté
    ahí. Las credenciales salen del entorno del contenedor —las mismas dos
    variables que encienden el auto-login— y nunca de la línea de comandos.
    """
    usuario = os.environ.get("DEMO_USERNAME", "").strip()
    clave = os.environ.get("DEMO_PASSWORD", "")
    if not usuario or not clave:
        return None
    # `base` sólo existe en el `Api` real. La suite corre el seed contra un
    # doble que habla directo con la app, sin URL: ahí no hay segunda sesión
    # que abrir, y el tramo cae al camino del usuario que corre el seed.
    base = getattr(api, "base", None)
    if not base:
        return None
    sesion = Api(base)
    try:
        sesion.post("/api/login", {"username": usuario, "password": clave})
    except RuntimeError as e:
        print(f"  -- no se pudo entrar como {usuario}: {e}")
        return None
    return sesion


def _sembrar_operacion(api: Api, clientes: dict, productos: dict, contar) -> None:
    """Un día de operación: turno de caja, ventas, facturas, recibos, cobranza
    de cuenta corriente, movimientos de caja y egresos.

    Sale de medir la demo: **ventas, facturas, caja, egresos, cuenta corriente,
    recibos y turnos estaban los siete en cero**, o sea siete pantallas del
    menú que se abrían vacías.

    🔴 **Las facturas se emiten SIN CAE, y eso es a propósito.** El módulo habla
    con ARCA de verdad, pero `solicitar_cae()` corta apenas ve que la instancia
    no tiene certificado configurado —y una demo no lo tiene—, así que el
    comprobante nace como documento interno: se ve la pantalla, el detalle y el
    PDF con su maqueta real, sin pedir un CAE contra el padrón ni emitir nada
    fiscal desde una demo pública. Decidido con el humano el 2026-08-06.
    """
    # ── Turno de caja, abierto POR EL VISITANTE ───────────────────────────
    # 🔴 `GET /api/turnos` filtra por usuario cuando quien pregunta no es
    # admin (`usuario_id=None if es_admin else user["id"]`), y eso está bien:
    # un cajero ve sus turnos, no los de todos. Pero el seed corre como
    # **admin**, así que un turno abierto por él le queda invisible al
    # visitante y la pantalla se le abre vacía igual.
    #
    # Por eso esto se hace con una sesión del propio usuario de la demo. Es la
    # regla general para todo lo que el producto ordena por usuario: sembrarlo
    # con el usuario que lo va a mirar, no con el que tiene permisos.
    visitante = _sesion_del_visitante(api)
    if visitante is not None:
        if not _lista(visitante.get("/api/turnos")):
            try:
                visitante.post("/api/turnos/abrir", {
                    "monto_inicial": 25000,
                    "notas": "Apertura de caja de la demo",
                })
                contar("turno", True)
            except RuntimeError as e:
                print(f"  -- turno del visitante: {e}")
    else:
        # Sin credenciales de visitante (dev, por ejemplo) el turno se abre con
        # el usuario que corre el seed: alcanza para que la caja opere.
        if not _lista(api.get("/api/turnos")):
            try:
                api.post("/api/turnos/abrir", {
                    "monto_inicial": 25000, "notas": "Apertura de caja",
                })
                contar("turno", True)
            except RuntimeError as e:
                print(f"  -- turno: {e}")

    medios = _lista(api.get("/api/ventas/medios-pago")) or ["Efectivo"]
    def medio(preferido: str) -> str:
        # Los medios los define la instancia; si el preferido no está, se usa
        # el primero en vez de inventar uno que el backend rechace.
        planos = [m if isinstance(m, str) else (m.get("nombre") or m.get("id"))
                  for m in medios]
        return next((m for m in planos if preferido.lower() in str(m).lower()),
                    planos[0])

    def item(codigo: str, nombre: str, qty: int, precio: float) -> dict:
        return {"nombre": nombre, "qty": qty, "precio": precio,
                "producto_id": productos.get(codigo)}

    # ── Ventas: contado y a cuenta corriente ──────────────────────────────
    # La de cuenta corriente es la que después deja saldo y permite cobrar:
    # sin ella, las pantallas de cuenta corriente y recibos quedan vacías.
    ventas_spec = [
        ("Verónica Aguilar", [item("PAP-001", "Resma A4 75 g", 3, 8500)],
         [(medio("efectivo"), 25500)], "Venta de mostrador"),
        ("Colegio Santa Rita", [item("PAP-002", "Cuaderno tapa dura", 20, 4200),
                                item("PAP-003", "Bolígrafo azul x50", 2, 12000)],
         [(medio("tarjeta"), 108000)], "Venta con tarjeta"),
    ]
    ventas_hechas = {v.get("observaciones") for v in _lista(api.get("/api/ventas"))}
    venta_contado = None
    for cliente, items, pagos, obs in ventas_spec:
        if obs in ventas_hechas:
            continue
        total = sum(m for _, m in pagos)
        try:
            venta = api.post("/api/ventas", {
                "fecha": HOY.isoformat(),
                "cliente_id": clientes.get(cliente),
                "items": [i for i in items if i["producto_id"]],
                "pagos": [{"medio": md, "monto": mo, "referencia": ""}
                          for md, mo in pagos],
                "observaciones": obs,
            })
            contar("ventas", True)
            venta_contado = venta_contado or venta
            _ = total
        except RuntimeError as e:
            print(f"  -- venta de {cliente}: {e}")

    # Recibo de una venta: la pantalla de recibos estaba vacía y el recibo es
    # lo que el cliente se lleva.
    if venta_contado and not _lista(api.get("/api/recibos")):
        try:
            api.post(f"/api/recibos/venta/{venta_contado['id']}", {})
            contar("recibos", True)
        except RuntimeError as e:
            print(f"  -- recibo de venta: {e}")

    # ── Facturas internas (sin CAE) ───────────────────────────────────────
    if not _lista(api.get("/api/facturas")):
        for tipo, cliente, items in (
            (6, "Distribuidora del Oeste SRL",
             [("Mouse inalámbrico", 4, 18000), ("Teclado USB", 4, 22000)]),
            (11, "Verónica Aguilar",
             [("Instalación de impresora", 1, 25000)]),
        ):
            try:
                api.post("/api/facturas", {
                    "tipo": tipo, "fecha": HOY.isoformat(),
                    "client_id": clientes.get(cliente),
                    "items": [{"description": d, "qty": c, "unit_price": p}
                              for d, c, p in items],
                    "tax_rate": 0.21, "condicion_venta": "Contado",
                    "observations": "Comprobante interno de la demo (sin CAE).",
                })
                contar("facturas", True)
            except RuntimeError as e:
                print(f"  -- factura tipo {tipo}: {e}")

    # ── Cuenta corriente: un cargo y una cobranza parcial ─────────────────
    # El cargo entra como movimiento de caja del tipo que corresponda; la
    # cobranza genera su recibo, que es el segundo tipo de recibo del producto.
    cliente_cc = clientes.get("Estudio Contable Bianchi")
    if cliente_cc and not _lista(api.get("/api/cuenta-corriente")):
        try:
            api.post(f"/api/cuenta-corriente/{cliente_cc}/pagar", {
                "monto": 40000, "fecha": HOY.isoformat(),
                "concepto": "Pago a cuenta", "medio_pago": medio("efectivo"),
                "referencia": "Recibo de la demo",
            })
            contar("cobranzas", True)
        except RuntimeError as e:
            print(f"  -- cobranza: {e}")

    # ── Caja: movimientos manuales ────────────────────────────────────────
    if not _lista(api.get("/api/caja")):
        for tipo, concepto, monto in (
            ("ingreso", "Aporte del socio", 50000),
            ("egreso", "Compra de insumos de limpieza", 12500),
        ):
            try:
                api.post("/api/caja", {
                    "fecha": HOY.isoformat(), "tipo": tipo, "concepto": concepto,
                    "monto": monto, "medio_pago": medio("efectivo"),
                    "referencia": "Movimiento de ejemplo",
                })
                contar("caja", True)
            except RuntimeError as e:
                print(f"  -- caja {tipo}: {e}")

    # ── Egresos con comprobante ───────────────────────────────────────────
    #
    # 🔴 Dos cosas que se aprendieron midiendo el export, no leyendo el código:
    #
    # 1. **El Libro de IVA Compras sólo toma `tipo_comprobante = 'factura'`**
    #    (`libracore.db.libros_iva.get_egresos_para_iva`, filtro en el SQL). Con
    #    egresos sueltos —que es lo que sembraba antes— la pantalla de Libros de
    #    IVA mostraba las ventas y el lado de compras salía **vacío**, y el
    #    export bajaba un archivo de 0 bytes.
    # 2. **`iva_pct` es una fracción, no un porcentaje.** El backend hace
    #    `monto_neto * iva_pct` sin dividir por 100, y el frontend lo muestra
    #    con `Math.round(iva_pct * 100)`. Mandar `21` no da un 21%: le puso
    #    $588.000 de IVA a un gasto de $28.000.
    #
    # Y el número de comprobante importa: el export lo parte en punto de venta
    # y número (`_parse_num_egreso`), así que sin él el archivo sale con ceros.
    proveedores = {p["nombre"]: p["id"] for p in _lista(api.get("/api/proveedores"))}
    if not _lista(api.get("/api/egresos")):
        for concepto, categoria, neto, prov, numero in (
            ("Resma A4 y papelería", "Mercadería / Materias primas", 96000,
             "Papelera Central SA", "0003-00001842"),
            ("Notebooks para administración", "Otros", 740000,
             "Insumos Tecnológicos SRL", "0007-00000315"),
            ("Alquiler del local", "Alquiler", 320000, None, ""),
            ("Servicio de internet", "Servicios (luz, gas, internet)", 45000, None, ""),
            ("Combustible del reparto", "Transporte", 28000, None, ""),
        ):
            try:
                api.post("/api/egresos", {
                    "fecha": HOY.isoformat(), "concepto": concepto,
                    "categoria": categoria, "monto_neto": neto, "iva_pct": 0.21,
                    # Con proveedor y número es una factura de compra y entra al
                    # libro; sin ellos es un gasto interno y no entra. Los dos
                    # casos están a propósito: la pantalla de egresos muestra la
                    # diferencia.
                    "tipo_comprobante": "factura" if prov else "otro",
                    "numero": numero,
                    "proveedor_id": proveedores.get(prov),
                    "observaciones": "Gasto de ejemplo de la demo",
                })
                contar("egresos", True)
            except RuntimeError as e:
                print(f"  -- egreso {concepto}: {e}")



def _cargar_logo(api, nombre: str, inicial: str, color: tuple, contar) -> None:
    """Dibuja el logo del negocio y lo sube a Configuración.

    🔴 **Se genera, no se commitea.** PIL viene en la imagen del producto, así
    que el seed lo dibuja en el momento: no hay binarios en el repo y cambiar
    el color es cambiar una línea. Mismo criterio que el resto del seed — el
    estado limpio es código, no un archivo guardado a mano.

    Sin logo, los PDF de la demo salen con un hueco arriba: el interesado ve
    dónde iría el suyo pero no cómo se ve.

    ⚠️ El campo del multipart se llama **`logo`**, no `file`: con `file` la API
    contesta 422. Está leído del openapi de la instancia.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("  (sin PIL: se saltea el logo)")
        return

    # 🔴 La ruta de configuración no es la misma en todos los productos, y
    # pedir la que no existe **no da 404**: el catch-all de la SPA contesta
    # 200 con el index.html y el parseo revienta. Así que la guarda no puede
    # depender de acertarla: ante cualquier duda se sube el logo, que es
    # inocuo, en vez de arriesgar quedarse sin él.
    for ruta in ("/api/config/empresa", "/api/config"):
        try:
            actual = api.get(ruta)
        except Exception:
            continue
        if isinstance(actual, dict):
            plano = str(actual)
            if '"logo"' in plano or "'logo'" in plano:
                if any("logo" in str(k) and v for k, v in actual.items()):
                    contar("logo", False)
                    return
            break

    imagen = Image.new("RGBA", (520, 160), (255, 255, 255, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rounded_rectangle((8, 20, 128, 140), radius=24, fill=color)
    dibujo.text((52, 60), inicial, fill=(255, 255, 255))
    dibujo.text((150, 55), nombre, fill=(30, 30, 30))
    dibujo.line((150, 95, 150 + min(340, len(nombre) * 11), 95), fill=color, width=4)

    # 🔴 La subida es multipart a mano, así que necesita la URL y el opener del
    # `Api` real. La suite corre el seed contra un doble que habla directo con
    # la app y no tiene ninguno de los dos: sin esta guarda, `api.base`
    # reventaba con AttributeError y se llevaba puestos **11 tests** del seed
    # entero, no sólo el del logo.
    if not getattr(api, "base", None) or not getattr(api, "opener", None):
        return

    import io
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")

    limite = "----seed" + "0" * 12
    cuerpo = (
        f"--{limite}\r\n"
        'Content-Disposition: form-data; name="logo"; filename="logo.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + buffer.getvalue() + f"\r\n--{limite}--\r\n".encode()

    import urllib.request
    pedido = urllib.request.Request(
        f"{api.base}/api/config/empresa/logo", data=cuerpo, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={limite}"},
    )
    try:
        api.opener.open(pedido, timeout=30)
        contar("logo", True)
    except Exception as e:
        print(f"  -- logo: {e}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--usuario", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument(
        "--force", action="store_true",
        help="Correr contra una URL que no parece de dev ni de demo. No usar.",
    )
    args = ap.parse_args()

    if not url_no_productiva(args.url) and not args.force:
        print(f"ERROR: {args.url} no parece una instancia de dev ni de demo.",
              file=sys.stderr)
        print("Este script NO se corre contra la instancia de un cliente.",
              file=sys.stderr)
        return 2

    api = Api(args.url)
    api.post("/api/login", {"username": args.usuario, "password": args.password})
    sembrar(api)
    return 0


if __name__ == "__main__":
    sys.exit(main())
