# Changelog

## Sin publicar — 2026-10-16

### Pin libra-ui v0.158.1: el cliente de la factura se puede dar de alta ahí mismo (ADR-071 del kit, sin migración)

- Pin: **libra-ui `v0.158.1`** (antes `v0.157.0`). **Sin migración y sin cambio en el backend.** `package-lock.json` sube también `@playwright/test`/`playwright` a 1.64.1, que es el rango que pide el kit (`peerDependencies`).
- **`/facturas/nueva`: el campo «Cliente» es ahora `SelectCliente`** (`frontend/src/pages/FacturaNueva.tsx`): el buscador de siempre (con la × para volver a «o nombre libre») y, al lado, el botón «Agregar nuevo cliente». El panel pide nombre, CUIT/DNI, condición frente al IVA, teléfono y email y da el alta en `POST /api/clientes` del motor (`crearYSumar` + `CAMPOS_CLIENTE_DEL_MOTOR` de `libra-ui/comercio/alta-de-cliente`). El recién creado se suma a la lista de la pantalla y queda elegido: la factura usa su CUIT para el aviso de FCE como el de cualquier otro cliente. Es el único campo de cliente propio del producto; el resto (Ventas, Presupuestos, Remitos) son pantallas del kit y ya lo traen.
- **Guard `frontend/src/test/campos-de-cliente.test.ts`** (`libra-ui/auditoria-de-clientes`, al lado de `selects-buscables.test.ts`): lee los fuentes y falla si un desplegable que elige un cliente no es `SelectCliente`. Un filtro que no crea nada se marca con `cliente-sin-alta: <motivo>`. Control positivo: mide al menos un campo. Comportamiento en `frontend/src/test/factura-cliente-alta.test.tsx`: crear el cliente hace `POST /api/clientes` con el nombre y queda elegido, su CUIT llega al aviso de FCE y un error del alta se ve en el panel sin elegir a nadie.

### La sucursal única «Casa central»: depósitos, cajas y ventas bajo una sola sucursal (libracommerce v0.63.0, revisión `0006_sucursal_unica`)

- **Nada visible cambia.** Contalibra es de un solo local, pero el motor ya tiene sucursales (ADR-063 de libracommerce) y todo quedaba en NULL; ahora cuelga de una sucursal predeterminada, «Casa central», para que el día que un cliente pida multisucursal no haya que migrar datos con él mirando. No se monta ninguna ruta ni pantalla de sucursales (`/api/sucursales` sigue sin existir): el kit sólo ofrece sucursal con dos o más. `tests/test_sucursal_unica.py` fija que depósitos, stock, listas de precio, cajas, turnos, ventas y resumen devuelven lo mismo salvo `branch_id`/`sucursal_id`.
- **Revisión de Alembic `0006_sucursal_unica`** (corre en `panel_admin actualizar`, después de `libracommerce-migrar`): crea la sucursal, le asigna los depósitos (también los inactivos) y las cajas sin sucursal, y completa `sales.branch_id` de las ventas de antes con la sucursal de su depósito (el criterio de `erp.margen`; las que no movieron stock quedan sin sucursal). Sin DDL. Idempotente. `downgrade` la deshace sólo si es la única sucursal, la predeterminada y se llama «Casa central» (si no, se niega y lo dice).
- **`init_db()`** llama la misma función (`app/sucursal_unica.py`) después de sembrar el «Depósito principal»: una instancia nueva nace con su sucursal y cada reinicio converge sin hacer nada.
- **El depósito que se crea cae en «Casa central»** (`OpcionesDepositos(sucursal_por_defecto=True)`) y **cada venta anota la sucursal de su depósito** (`sales.branch_id`, lo hace el motor).
- Requiere **libracommerce `v0.63.0`** (el pin se sube cuando exista el tag).

### Pines: libracore v1.173.0, libracommerce v0.62.0 y libra-ui v0.156.0 (sin migración); la consulta de CUIT sale del producto, fiar sin cliente se rechaza y la demo no muestra datos fiscales reales

- Pines: **libracore `v1.173.0`** (antes `v1.170.0`), **libracommerce `v0.62.0`** (antes `v0.60.0`) y **libra-ui `v0.156.0`** (antes `v0.153.0`); libraauth sigue en `v0.51.0`. **Sin migración.**
  - libracore `v1.171.0`: un cobro de factura no puede superar lo que falta (`POST /api/facturas/{id}/cobrar` da **409**, ADR-058). `v1.172.0`: las notas de crédito restan de lo pendiente (`pendiente = total − cobrado − acreditado`, ADR-059) y el cobro puede entrar por el turno (ADR-060; este producto no lo prende). `v1.173.0`: una demo no habla con ARCA ni muestra datos fiscales reales, y suma `libracore.demo.auditar_datos_fiscales` / `auditar_literales` (ADR-061).
  - libracommerce `v0.61.0`: fiar sin cliente se rechaza por default (**422**, `FiadoSinCliente`, ADR-061). `v0.62.0`: la creación del esquema se serializa entre procesos (ADR-062).
  - libra-ui `v0.154.0`: sin desborde a 390 px y contraste AA (ADR-067). `v0.155.0`: «Pendiente» y facturas «Acreditada» (ADR-068). `v0.156.0`: el error de la consulta de CUIT lleva al tutorial de Padrón A13 (ADR-069).
- **`GET /api/consultar-cuit/{cuit}` es el router del motor** (`libracore.consultar_cuit_router`), no un handler propio: sale de `app/web/app.py` y con él los shims `app/arca_wsaa.py` y `app/arca_wspadron.py` (nada los importaba). Mismo contrato (400, 503, 404, 403, 502, 500 y el JSON del padrón). **Cambia sin sesión:** se monta con `get_current_user_json` y no con `require_auth`, así que contesta **401** JSON en vez de redirigir (307) a `/login`, que rompía el `fetch` del kit (seguía la redirección y recibía el HTML del login). Test de contrato: `tests/test_consultar_cuit_contrato.py`.
- **`POST /api/integraciones/consultas` con un pago en cuenta corriente y sin CUIT da 422** (antes, con libracommerce `v0.61.0`, habría dado 500: `FiadoSinCliente` sin capturar). Una consulta sin CUIT va como Consumidor Final, sin cliente, y no hay deuda sin cliente. Con CUIT, fiar sigue andando.
- **`/facturas/nueva` sin desborde a 390 px** (`FacturaNueva.tsx`: el marco de la tabla con `min-w-0` y la tabla con `max-sm:overflow-x-auto`; el desplegable de sugerencias va en el flujo bajo `sm`). Es la copia local del formulario del kit (ADR-067).
- La semilla de la demo queda auditada: `tests/test_seed_demo.py` corre `auditar_literales` sobre `scripts/seed_demo.py` y `auditar_datos_fiscales` sobre la base sembrada con `DEMO_MODE=1`.
- E2E: `DESBORDE_A_390` y `CONTRASTE_CONOCIDO` quedan vacías (con el kit `v0.154.0` pasan las 72 mediciones) y los dos `test.fixme` de «no se puede cobrar más de lo que falta de una factura» y «una venta a cuenta corriente sin cliente se rechaza» se sacan: arreglados en libracore `v1.171.0` y libracommerce `v0.61.0`.

## Sin publicar — 2026-10-15

### Pines: libracore v1.170.0, libraauth v0.51.0 y libra-ui v0.153.0 (sin migración)

- Pines: **libracore `v1.170.0`** (antes `v1.168.0`), **libraauth `v0.51.0`** (antes `v0.50.0`) y **libra-ui `v0.153.0`** (antes `v0.152.1`). **Sin migración.** libracore `v1.169.0` suma `soltar_fk` (ADR-056; sin efecto en este producto, la usa LibraDesk). libracore `v1.170.0`: `delete_client` bloquea la baja de un cliente con cuenta corriente (`cc_pagos`, `cc_debitos`, `recibos` y `cc_asientos` con rol cliente; ADR-057) con un `ValueError` que dice que se puede desactivar. libraauth `v0.51.0`: el responsable puede aceptar por adelantado la próxima versión de los Términos (ADR-024). libra-ui `v0.153.0`: tras el gate de Términos, un aviso no bloqueante «Aceptar / Más tarde» (tarjeta abajo a la derecha, ADR-066). Efecto en este producto: la baja de un cliente sólo existe en la consola (`app/main.py`, opción «Eliminar»), que ya atiende el `ValueError`; la API no borra clientes.

## Sin publicar — 2026-10-13

### El producto queda listo para varios procesos y registra sus errores (ADR-044 y ADR-045 de libracore, ADR-023 de libraauth, ADR-053 de libra-ui)

- **Varios procesos por instancia (`uvicorn --workers N`), sin prenderlos: todo sigue en 1.** `WEB_CONCURRENCY` por defecto es 1 y el `docker-compose.yml` de dev pasa `--workers ${WEB_CONCURRENCY:-1}`; las instancias de cliente y demo corren el `CMD` del `Dockerfile`, que uvicorn ya hace respetar por `WEB_CONCURRENCY` sin tocarlo. Lo que se rompía con N procesos:
  - El hook de `startup` (`init_db`, el admin, el usuario de la demo, el depósito por defecto y la migración de secretos) corría en cada worker y un «si no existe, crear» se contestaba «no existe» en todos: ahora va dentro de `una_vez_al_arrancar("contalibra-arranque")`, de a un proceso por vez, y cada paso sigue preguntando adentro.
  - El anti-replay del captcha del login era un `dict` del proceso (un desafío resuelto servía una vez **por worker**): `captcha_usados=UsadosEnBase(...)` lo anota en la base de `usuarios` (`libraauth_captcha_usados`, migración `0003`).
  - El engine de `usuarios` lleva `pool_pre_ping=True`: tras un restore en caliente, el worker que no atendió el restore se recupera solo. **Después de un restore en caliente con más de un worker, reiniciar el contenedor.**
  - La nota de crédito sale por el router de facturas del motor, que ya le pasa su candado de base: este producto no emite notas por su cuenta y no cambia.
- **Registro de errores de la familia.** `instalar_registro_de_errores(app, "contalibra")` junto a `SecurityHeadersMiddleware`: un 500 responde `{"detail": "Error interno", "ref": "<8 hex>"}` y deja una línea en `DATA_DIR/errores/errores.jsonl`; `POST /api/errores-cliente` (público a propósito) recibe los errores del navegador. En el frontend, `instalarReporteDeErrores()` antes de montar y `<ErrorBoundary>` («Algo falló. Recargá la página.», con el `ref` si lo hay) alrededor de toda la app en `main.tsx`. El compose de `-dev` suma `LIBRA_ENTORNO=dev`, `LIBRA_INSTANCIA=contalibra-dev` y `LIBRA_VERSION`; las instancias de cliente y demo las reciben del panel en su próximo `actualizar`.
- Tests nuevos: `tests/test_registro_de_errores.py`, el replay del captcha contra la base (`tests/test_captcha_login.py`) y `tests/test_varios_procesos.py` (`uvicorn --workers 2` de verdad; marca `varios_procesos`). El doble del captcha de `tests/conftest.py` acepta ahora `(request, usados)`, como llama el router desde libraauth v0.50.0.
- Pines: libracore v1.157.0 → **v1.159.0** (sin migración), libraauth v0.49.0 → **v0.50.0** (**migración `0003_captcha_usados`**: el compose de dev, `scripts/panel_admin.py` y `scripts/nuevo_cliente.py` ya corren `libraauth-migrar upgrade` antes de arrancar, y `exigir_schema_al_dia` la exige), libra-ui v0.141.0 → **v0.142.1**, piso `uvicorn>=0.30.0`.

## Sin publicar — 2026-10-12

### Los clientes quedan en el log de actividad (ADR-043 de libracore, ADR-022 de libraauth)

- Antes el alta, la edición, la baja, el fiado y la ficha de un cliente (`/api/clientes`) **no dejaban rastro de quién los tocó**. Ahora el motor de core (`libracore` v1.157.0) le avisa cada escritura de `clients` a un registrador, dentro de la misma transacción, y este producto le enchufa el de `libraauth` (v0.49.0, `registrador_dbapi`) en `app/web/app.py`. Un log roto bloquea la escritura en vez de perderse en silencio.
- La fila dice **quién** fue: `agregar_middleware_de_usuario` sella el usuario de la cookie de sesión en cada request (sin él quedaría «Sistema»).
- La pantalla de Logs los muestra como tipo **Cambios** (`actividad`), sin pantalla nueva: «Cliente — Ana Pérez (edición)». El detalle del diff queda en `actividad_log.cambios`, que la pantalla todavía no muestra.
- Guardar sin cambios no deja fila. Sin migración (la tabla `actividad_log` ya la crea `init_schema` de libracommerce). Pines: libracore v1.157.0, libraauth v0.49.0 y libracommerce v0.57.0 (este producto no usa su `RepositorioAuditado`).

## Sin publicar — 2026-10-07

### El menú y los títulos usan el catálogo de íconos de la familia (ADR-035)

- Cada concepto lleva **un solo ícono**, en el menú y en el título de su pantalla, igual en todos los productos. El menú y los títulos de este
  producto lo toman de `ICONOS` (`libra-ui/iconos-identidad`) y no de un `import` suelto de lucide.
- Cambian: **Listas de precio** `Tag` → `Tags`, **Log de actividad** `History` → `ScrollText`, **Caja** `SquareStack` → `Wallet` y **Caja por medio** `Wallet` → `Coins`.
- Un test nuevo (`frontend/src/test/iconos-del-catalogo.test.ts`) falla si una entrada del menú vuelve a usar otro ícono que el de su concepto.
- Pin: `libra-ui` v0.123.0 → **v0.125.0**.

## v1.6.4 — 2026-08-30

### La pantalla dice de qué ambiente es el token de MercadoPago

- 🔴 **MercadoPago no tiene homologación como ARCA.** No hay host de sandbox:
  es el mismo `api.mercadopago.com` para los dos y **lo que define el ambiente
  es el token**. Hasta ahora la pantalla no lo decía en ningún lado, y las dos
  fallas son mudas — un token de producción en una instancia `dev` **cobra
  plata de verdad**, y uno de prueba en la instancia de un cliente **no cobra
  nada**. Las dos se ven igual: el QR se genera y la orden se crea.
  > Ahora la tarjeta muestra `Ambiente de prueba`, `Ambiente de producción` o
  > `Ambiente sin verificar`, con la fecha en que se determinó.
- **Mirar el prefijo del token no alcanza**, y ahí está toda la dificultad: un
  *usuario de prueba* de MercadoPago entrega credenciales `APP_USR-` igual que
  las reales, y lo único que lo delata es el `nickname` de `/users/me`. Por eso
  quien clasifica es **Probar conexión** — que además ahora recarga la sección,
  porque probar es justamente lo que averigua el ambiente.
- La clasificación guardada lleva la **huella** del token sobre el que se
  determinó: si la credencial cambia por cualquier vía —la pantalla,
  `panel_admin`, restaurar un backup— se descarta sola. Sin eso, pasar la
  instancia de prueba a producción dejaría el cartel diciendo "prueba" sobre
  una credencial real.

### Pines

- `libracore` v1.64.0 → **v1.65.0**
- `libra-ui` v0.53.0 → **v0.54.0**

## v1.6.3 — 2026-08-30

### Una sola configuración de correo

- 🔴 **Este producto tenía DOS configuraciones de SMTP, y no se veía cuál
  mandaba qué.** La de la pantalla escribía la base cifrada de libraauth
  (`/api/config/smtp`); la que mandaba **comprobantes y presupuestos** leía
  `email_smtp_*` de `config.json`. El síntoma era mudo: el cliente cargaba su
  contraseña de aplicación, la pantalla decía "Guardado", y los mails seguían
  saliendo por la otra —o no salían—. No fue un diseño: la de comprobantes
  nació antes y quedó donde estaba.
  > Ahora hay una sola. La sección de correo es la del kit, contra
  > `/api/config/smtp`, igual que en los otros siete productos, y los **tres**
  > envíos —comprobantes, presupuestos y `GET /api/email/probar`— resuelven por
  > `libracore.facturas_router.smtp_efectivo` (LibraCore v1.64.0). Que los tres
  > lo resolvieran por su cuenta es exactamente como aparecieron los dos stores.
- **`GET` y `PUT /api/config/email` se retiraron.** Eran el único escritor del
  store viejo. Las claves `email_smtp_*` de `config.json` **se siguen leyendo**
  como red de seguridad, pero ya no las escribe nadie.
- **No hubo migración de datos, y se verificó por qué no hacía falta.** Se
  relevaron las 7 instancias de la flota que mandan comprobantes: 6 tienen
  `config.json` vacío y el SMTP en el entorno —o sea que hasta hoy **no podían
  mandar un comprobante por mail**, con un servidor perfectamente usable
  configurado—, y la séptima, producción, tiene en `config.json` los mismos
  valores que en el entorno: la misma casilla. Copiarlos a la base sólo habría
  agregado una tercera copia cifrada de las mismas credenciales.
- **El botón *Probar conexión* queda propio.** `GET /api/email/probar` existe
  acá y en Restolibra y en los otros seis no; subirlo al kit pondría en pantalla
  un botón que en seis productos daría 404. Prueba el mismo SMTP que la sección
  configura, porque el endpoint resuelve por el mismo camino que el envío.

## v1.6.2 — 2026-08-29

### El reloj de la base

- **Los `created_at` dejan de estampar UTC.** El DEFAULT de las columnas con
  reloj era `datetime('now')`, que en SQLite es UTC y que el adaptador de
  PostgreSQL traduce a UTC **a propósito**, para que las dos bases guarden el
  mismo texto. O sea que las dos guardaban la hora equivocada, y de la misma
  manera. Pasa a `datetime('now','-3 hours')`, el mismo offset fijo de
  `_ar_now()`.
  > Se entró buscando el cron nocturno de MercadoPago, porque ahí se veía
  > (`03:00:06` cuando en Argentina eran las `00:00:06`). **El cron no tenía
  > nada**: ninguna ruta de código pasa `created_at`, lo pone el DEFAULT. Las
  > filas escritas a mano estaban igual de corridas y sólo pasaban por buenas
  > porque una operación de las 12:56 guardada como `15:56` sigue pareciendo
  > horario de trabajo. Se confirmó cruzando el log del contenedor con los
  > movimientos que ese click escribió.
  > Es la mitad que faltaba del barrido de huso del 2026-08-23: aquél movió los
  > relojes de los **procesos**, éste el que estampa **la base**.
- **Presupuestos vencidos, un día antes.** `date('now')` también era UTC, así
  que entre las 21:00 y la medianoche marcaba vencido un presupuesto que todavía
  valía.

> ⚠️ **Las filas ya escritas no se tocan.** Quedan 3 h adelantadas y hay una
> discontinuidad a partir de este deploy, igual que la que dejó el 2026-08-23 y
> por el mismo motivo. Decisión del humano el 2026-08-29.

### Motores

- `libracore` a `v1.60.1` y `libracommerce` a `v0.9.1`.

## v1.6.1 — 2026-08-29

Deploy a producción de lo acumulado en `develop`. **Nueve commits**, no siete:
las dos instancias de producción venían de una imagen construida antes del
último merge a `main`, así que el rango real se midió desde el commit que la
imagen declara (`org.libra.commit`) y no desde `main`.

### Caja

- **Un movimiento de caja se anula, no se borra.** Borrar dejaba el arqueo con
  un agujero que nadie puede auditar. Los anulados quedan tachados **y** con la
  palabra «anulado» —sólo el tachado se pierde en una impresión en blanco y
  negro y no lo lee un lector de pantalla—, y el botón de anular desaparece en
  esas filas en vez de quedar deshabilitado.
  > La columna `caja_movimientos.anulado` **la agrega el arranque**
  > (`init_core_schema`), de forma idempotente y también sobre PostgreSQL.
  > Verificado antes del deploy: ninguna de las instancias la tenía, y la de
  > LibraClub —que ya corre el motor nuevo— sí.

### Comprobantes

- Los comprobantes salen **del motor** y no de una copia local.
- El listado de comprobantes y la bandeja de MercadoPago pasan a `libra-ui`
  (v0.43.0); acá queda un shim con lo que es propio del producto. La bandeja
  bajó de 509 líneas a 14.

### Motor

- `libracore` v1.54.0 → **v1.59.0**. Sin migraciones nuevas del motor en ese
  salto (sólo existen `0001_baseline` y `0002`, las dos anteriores a v1.54.0).
- `libraauth` v0.34.0 — la demo deja de estar frenada por el gate de Términos.

---

## v1.3.0 — 2026-05-27

### Nuevos módulos

- **Egresos**: módulo completo de gastos. ABM de egresos con categorías configurables, tipo de comprobante (factura / ticket / recibo / otro), número de comprobante, IVA (0 / 10,5 % / 21 %), estado de pago (pendiente / parcial / pagado) y observaciones. Pagos registrables con medio de pago, referencia y caja — cada pago genera un movimiento de caja tipo `egreso`. Filtros por período, categoría, estado y proveedor.
- **Proveedores**: ABM de proveedores (razón social, CUIT/DNI, email, teléfono, domicilio, condición IVA) con vista de detalle que lista los egresos asociados. Buscador con endpoint JSON `/api/proveedores/buscar`. Aparece como submenú dentro de la sección Egresos en el sidebar.
- **Categorías de egreso**: administradas desde `/config/categorias-egreso`. 10 categorías por defecto (Mercadería, Alquiler, Servicios, Sueldos, etc.). Accesibles desde el formulario de egreso.
- **Tesorería**: módulo para llevar el saldo de múltiples cuentas (banco, efectivo, billetera digital, otro). Cada cuenta tiene saldo inicial configurable; el saldo actual se calcula en tiempo real sumando ingresos y restando egresos. Movimientos (ingreso / egreso) registrables con concepto, referencia y fecha. **Transferencias entre cuentas**: crea automáticamente dos movimientos enlazados (salida del origen + entrada al destino). Tabla de últimos movimientos consolidada. Visible en sidebar bajo sección "Tesorería".

### Recibos de pago (PDF)

- **Recibo desde factura**: botón "Recibo" (verde) en el detalle de la factura, disponible cuando hay cobros registrados. Genera PDF A4 con datos del emisor, datos del cliente, monto destacado en teal, concepto ("Cancelación de FACTURA C N° 0005-00000001 del 27/05/2026"), tabla de pagos (fecha / medio / referencia / monto) y espacio para firma y sello.
- **Recibo desde venta**: el mismo botón aparece en el detalle de la venta cuando tiene pagos registrados. El concepto referencia la venta ("Venta N° 47").
- `pdf_generator.generate_pdf_recibo(factura, cobros)` — función genérica que acepta tanto facturas como ventas. Devuelve bytes directamente (sin escribir a disco).

### Cobro de facturas — mejoras

- **Modal de cobro con pagos parciales**: reemplaza el botón POST simple. Permite especificar monto (pre-llenado con el pendiente), fecha, caja (selector si hay múltiples), medio de pago (cargado dinámicamente desde `/cajas/{id}/medios`) y referencia.
- **Historial de cobros**: la vista de factura muestra todos los cobros registrados con fecha, badge de medio y referencia. Tres estados: pagado completo (verde), pago parcial (amarillo con pendiente), pendiente (gris).

### Formulario de nueva factura

- **Selector de cliente limpio**: elimina los campos manuales en favor de hidden inputs siempre presentes. "Consumidor Final" es la opción por defecto. Al seleccionar un cliente almacenado se muestra una tarjeta read-only con sus datos. Botón "+" para crear cliente rápido sin salir del formulario (mismo modal que Nueva Venta).

### Remitos — sin precios

- Los remitos son ahora comprobantes de entrega de mercadería sin valor fiscal: la tabla de ítems muestra solo Descripción y Cantidad. Se eliminaron los campos de precio, IVA y totales del formulario, la vista de detalle, la lista y el PDF. Los valores monetarios se almacenan en 0 en la base de datos para compatibilidad.

### Zona horaria Argentina

- `_ar_now()` en `database.py`: helper que devuelve la hora actual en UTC-3 (America/Argentina/Buenos_Aires, sin DST) usando `zoneinfo`. Se usa en `create_turno()` y `cerrar_turno()` para que la apertura y el cierre del turno muestren la hora local correcta en lugar de UTC.

### Fixes

- **Ticket en blanco** (`ticket_generator.py`): `_recortar_pdf_a_contenido` ahora prepend un operador `cm` al content stream del PDF para trasladar las coordenadas del contenido al área visible de la página recortada. fpdf2 v2.8.7 cambió `pages[n]` de dict a `PDFPage` — `page.set_dimensions()` cambia el MediaBox pero no las coordenadas del stream; el `cm` corrige el desfase.
- **PDF factura — nombre de empresa largo**: `_draw_card` usa `multi_cell` en lugar de `cell` para el valor de cada campo. La altura del card se mide con `multi_cell(..., split_only=True)` antes de dibujar, expandiéndose si la razón social requiere más de una línea.

### Estructura nueva

```
web/routers/
├── egresos.py          ← NUEVO: CRUD de egresos + pagos
├── proveedores.py      ← NUEVO: ABM de proveedores
└── tesoreria.py        ← NUEVO: cuentas + movimientos + transferencias

web/templates/
├── egresos/
│   ├── list.html       ← lista con resumen (total / pagado / pendiente)
│   ├── form.html       ← formulario nuevo egreso con cálculo IVA en vivo
│   └── detail.html     ← detalle con banner de estado y modal de pago
├── proveedores/
│   ├── list.html       ← listado con buscador
│   ├── form.html       ← ABM
│   └── detail.html     ← ficha con egresos asociados
├── tesoreria/
│   ├── list.html       ← tarjetas por cuenta + últimos movimientos + modal transferencia
│   ├── cuenta_form.html← alta/edición de cuenta
│   └── detail.html     ← movimientos de una cuenta + modal nuevo movimiento + modal transferencia
└── config/
    └── categorias_egreso.html  ← NUEVO: ABM de categorías

database.py             ← +180 líneas: tablas y CRUD de egresos, proveedores y tesorería
pdf_generator.py        ← +220 líneas: generate_pdf_recibo(), corrección de card height
ticket_generator.py     ← fix: coordinate transform en _recortar_pdf_a_contenido
```

---

## v1.2.0 — 2026-05-26

### Nuevas funcionalidades

- **Facturación automática MP por cliente**: clientes con `auto_facturar` habilitado generan factura + email automáticamente al llegar un pago aprobado de MercadoPago. Toggle switch CSS3 en ficha de cliente y formulario de edición.
- **Ficha de cliente**: nueva vista `/clientes/{id}` con datos, resumen (facturas/presupuestos/remitos) y todos los comprobantes asociados. El nombre del cliente es clickeable desde cualquier tabla.
- **Registro de accesos**: login, logout e intentos fallidos quedan registrados en Logs del sistema con IP, usuario y timestamp.
- **Usuario en logs de actividad**: facturas, caja, remitos y presupuestos ahora registran qué usuario los creó (migración de columna `usuario_id` en las 4 tablas).
- **Toggle switches CSS3**: reemplaza botones de texto en módulos del sistema y auto-factura con switches deslizantes animados, definidos una sola vez en `base.html`.
- **Entornos dev/prod separados**: rama `develop` → contenedor `contalibra-dev` (puerto 8071, hot-reload, DB aislada). Rama `main` → contenedor `contalibra` (puerto 8070, imagen fija). Script `scripts/deploy-prod.sh` para promover cambios.
- **Versioning interno**: `version.py` con semver visible en el sidebar. Badge `DEV` en entorno de desarrollo. Git tags en cada release.

### Mejoras de UI/PDF

- **Formato monetario argentino unificado**: filtros Jinja2 `|moneda`, `|moneda0` y `|entero` aplicados en toda la UI (punto miles, coma decimal: `1.234,56`). JS actualizado en formularios de ventas, facturas y presupuestos.
- **PDF — descripción de ítems con wrap**: las descripciones largas ahora se parten en múltiples líneas en lugar de truncarse. Altura de fila calculada dinámicamente.
- **PDF — condición de venta**: se lee desde la base de datos en lugar de mostrar siempre "Contado".
- **PDF — totales anclados al pie**: el bloque subtotal/IVA/total siempre aparece en la parte baja de la página, sin importar la cantidad de ítems.
- **Cantidades como enteros**: stock, cantidades de ítems y movimientos se muestran sin decimales (`1` en lugar de `1,00`).

### Integración MercadoPago

- **Bandeja de pagos MP**: módulo completo con webhook HMAC, sincronización de transferencias bancarias, facturación manual/automática, creación de clientes y reenvío de email.
- **Concepto editable**: descripción del pago MP usada como concepto de factura en auto-facturación.
- **"Bank Transfer" oculto**: strings internos de la API de MP no se muestran en la columna Banco/Billetera.

### Fixes

- Venta presencial con QR: `venta['items']` en lugar de `venta.items` en template.
- WAL files de SQLite removidos del tracking de git.
- Módulo `mp_facturacion.py` extraído como código compartido entre webhook y bandeja manual.

---

## v1.0.0 — 2026-05-12

Versión inicial estable. Base completa del sistema Contalibra.

### Módulos incluidos

| Módulo | Descripción |
|--------|-------------|
| Facturación | Facturas A/B/C, Notas de Crédito y Débito con autorización ARCA (AFIP) |
| Remitos | Generación y gestión de remitos con PDF |
| Presupuestos | Presupuestos con conversión a remito/factura y PDF |
| Clientes | ABM de clientes con historial |
| Caja | Registro de movimientos de caja (ingresos/egresos), integración con MercadoPago |
| Config | Configuración de empresa, ARCA/AFIP, logo, condiciones de pago |
| Dashboard | Resumen financiero con totales del período |
| Multi-usuario | Roles admin y operador, hash PBKDF2-SHA256, sesiones con itsdangerous |

### Infraestructura

- Contenedor Docker por cliente (imagen `contalibra:latest`)
- Script de onboarding: `scripts/nuevo_cliente.py`
- Panel de administración CLI: `scripts/panel_admin.py`
- Proxy SSL automático via Nginx Proxy Manager API: `scripts/npm_api.py`, `scripts/npm_setup.py`

### Integraciones

- **ARCA (AFIP)**: WSAA (autenticación con certificado digital) + WSFE (autorización electrónica) + WSPadron A4
- **MercadoPago**: webhook de notificaciones, registro automático en caja
- **Email**: envío de comprobantes PDF por SMTP

### Stack técnico

- Backend: Python 3.11, FastAPI, SQLite, itsdangerous
- PDF: fpdf2 2.8.7
- Frontend: Bootstrap 5.3, Bootstrap Icons
- Deploy: Docker, Nginx Proxy Manager, Let's Encrypt
