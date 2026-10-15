import { randomUUID } from 'node:crypto'
import { expect, type APIRequestContext, type APIResponse } from '@playwright/test'

// Lo que cada spec necesita sembrar, por la API: los mismos endpoints que usa la pantalla. **Cada spec arma lo suyo con
// nombres únicos** (`unico`): no depende del orden, ni de lo que dejó otro, ni de la semilla de la demo (que además deja un
// turno del admin abierto).

/** Un nombre que no se repite entre corridas ni entre specs: la instancia de prueba (o dev, de noche) acumula datos. */
export function unico(base: string): string {
  return `${base} ${randomUUID().slice(0, 8)}`
}

/** Un monto como lo muestra la SPA (`es-AR`): `$ 12.000,00`, y `−$ 150,00` el negativo (con el signo menos de verdad, U+2212, en las
 *  tablas del kit; en otros lugares el guion). Se compara con `\s` y no con un espacio: el kit usa un espacio duro. */
export function pesos(monto: number): RegExp {
  const numero = Math.abs(monto).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return new RegExp(`${monto < 0 ? '[-\u2212]' : ''}\\$\\s?${numero.replace(/[.,]/g, (c) => `\\${c}`)}`)
}

/** Un CUIT con forma de CUIT que no se repite (la ficha de clientes no admite dos con el mismo). El dígito verificador no se valida al dar de alta. */
export function cuitUnico(): string {
  const cuerpo = String(Math.floor(10_000_000 + Math.random() * 89_999_999))
  return `20-${cuerpo}-${Math.floor(Math.random() * 10)}`
}

export async function json<T = Record<string, unknown>>(respuesta: APIResponse, contexto: string): Promise<T> {
  const cuerpo = await respuesta.text()
  expect(respuesta.ok(), `${contexto} -> ${respuesta.status()}: ${cuerpo.slice(0, 300)}`).toBe(true)
  return (cuerpo ? JSON.parse(cuerpo) : null) as T
}

/** La fecha ISO (`AAAA-MM-DD`) de hoy en Buenos Aires, que es la fecha con la que el motor arma los movimientos del día. */
export function hoy(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'America/Argentina/Buenos_Aires' })
}

// ── Clientes y productos ────────────────────────────────────────────────────

export type Producto = { id: number; nombre: string; precio: number }
export type Cliente = { id: number; name: string; cuit_dni: string }

// Las lecturas que un spec repite DESPUÉS de varios segundos de navegador llevan `maxRetries`: Playwright reintenta sólo ECONNRESET
// («socket hang up»), que un GET puede repetir sin efecto; las escrituras no llevan reintento.

/** Un cliente nuevo, de los que no tienen deuda ni facturas. */
export async function crearCliente(
  api: APIRequestContext,
  { nombre = unico('Cliente e2e'), condicion = 'Consumidor Final' }: { nombre?: string; condicion?: string } = {},
): Promise<Cliente> {
  const cuit = cuitUnico()
  return json<Cliente>(
    await api.post('/api/clientes', { data: { name: nombre, cuit_dni: cuit, iva_condition: condicion } }),
    'POST /api/clientes',
  )
}

/** Un producto con stock (`entrada` por el ajuste de la pantalla de Stock). */
export async function crearProducto(
  api: APIRequestContext,
  { nombre = unico('Producto e2e'), precio, stock = 100 }: { nombre?: string; precio: number; stock?: number },
): Promise<Producto> {
  const creado = await json<{ id: number }>(
    await api.post('/api/productos', {
      data: { nombre, tipo: 'producto', precio_venta: precio, precio_costo: Math.round(precio / 2), stock_minimo: 0 },
    }),
    'POST /api/productos',
  )
  if (stock > 0) {
    await json(
      await api.post(`/api/stock/${creado.id}/ajuste`, { data: { modo: 'entrada', cantidad: stock, referencia: 'e2e' } }),
      'POST /api/stock/{id}/ajuste',
    )
  }
  return { id: creado.id, nombre, precio }
}

/** El stock que hay hoy de un producto. */
export async function stockDe(api: APIRequestContext, producto: { id: number }): Promise<number> {
  const datos = await json<{ stock_actual: number }>(await api.get(`/api/stock/${producto.id}`, { maxRetries: 3 }), 'GET /api/stock/{id}')
  return Number(datos.stock_actual)
}

// ── La caja y el turno ──────────────────────────────────────────────────────

export type Turno = {
  id: number; estado: string; usuario_id: number; monto_inicial: number
  monto_esperado_cierre: number | null; monto_declarado_cierre: number | null
}

/** Cierra todo turno abierto de la instancia, de quien sea. Un turno que dejó abierto un spec anterior (o la semilla, que abre el del
 *  admin, o una corrida cortada) ensuciaría el arqueo y los listados del que sigue. Lo hace el admin, que ve y cierra los de todos. */
export async function liberarCaja(admin: APIRequestContext): Promise<void> {
  const { turnos } = await json<{ turnos: Turno[] }>(await admin.get('/api/turnos'), 'GET /api/turnos')
  for (const turno of turnos.filter((t) => t.estado === 'abierto')) {
    await json(await admin.post(`/api/turnos/${turno.id}/cerrar`, { data: { monto_declarado: 0, notas: 'e2e: la caja se libera' } }), 'cerrar turno ajeno')
  }
}

/** Abre el turno de quien llama (`api`) con un fondo inicial, dejando la caja libre antes. Devuelve el id del turno. */
export async function abrirTurno(api: APIRequestContext, admin: APIRequestContext, montoInicial = 0): Promise<number> {
  await liberarCaja(admin)
  const turno = await json<{ id: number }>(
    await api.post('/api/turnos/abrir', { data: { monto_inicial: montoInicial, notas: 'e2e' } }), 'POST /api/turnos/abrir',
  )
  return turno.id
}

/** Cierra el turno abierto de quien llama, si tiene uno. Para el `finally` de cada spec: la caja queda libre aunque el test falle. */
export async function cerrarTurno(api: APIRequestContext): Promise<void> {
  const actual = await json<{ turno: { id: number } | null }>(await api.get('/api/turnos/actual'), 'GET /api/turnos/actual')
  if (!actual.turno) return
  await api.post(`/api/turnos/${actual.turno.id}/cerrar`, { data: { monto_declarado: 0, notas: 'e2e: cierre' } })
}

export async function turnoPorId(api: APIRequestContext, id: number): Promise<Turno> {
  const datos = await json<{ turno: Turno }>(await api.get(`/api/turnos/${id}`, { maxRetries: 3 }), 'GET /api/turnos/{id}')
  return datos.turno
}

export type MovimientoDeCaja = { id: number; tipo: 'ingreso' | 'egreso'; concepto: string; monto: number; anulado: number }

/** Los movimientos de caja de hoy que ve quien llama. */
export async function movimientosDeCaja(api: APIRequestContext): Promise<MovimientoDeCaja[]> {
  const desde = hoy()
  const datos = await json<{ movimientos: MovimientoDeCaja[] }>(
    await api.get('/api/caja', { params: { desde, hasta: desde }, maxRetries: 3 }), 'GET /api/caja',
  )
  return datos.movimientos
}

// ── Ventas ──────────────────────────────────────────────────────────────────

export type Venta = {
  id: number; numero: string; total: number; estado: string; cliente_id: number | null
  factura_id: number | null; turno_id: number | null; factura_display?: string | null; factura_cae?: string | null
}

/** Una venta por la API, en el medio de pago que se pida (`efectivo`, `tarjeta_debito`, `cuenta_corriente`...). */
export async function venderPorApi(
  api: APIRequestContext,
  producto: Producto,
  { cantidad = 1, medio = 'efectivo', cliente }: { cantidad?: number; medio?: string; cliente?: { id: number } } = {},
): Promise<Venta> {
  return json<Venta>(
    await api.post('/api/ventas', {
      data: {
        fecha: hoy(),
        cliente_id: cliente?.id ?? null,
        items: [{ nombre: producto.nombre, qty: cantidad, precio: producto.precio, producto_id: producto.id }],
        pagos: [{ medio, monto: producto.precio * cantidad }],
      },
    }),
    'POST /api/ventas',
  )
}

export async function ventaPorId(api: APIRequestContext, id: number): Promise<Venta> {
  return json<Venta>(await api.get(`/api/ventas/${id}`, { maxRetries: 3 }), 'GET /api/ventas/{id}')
}

// ── Cuenta corriente ────────────────────────────────────────────────────────

export type MovimientoCC = { tipo: 'debito' | 'credito'; concepto: string; monto: number; cc_pago_id: number | null }
export type CuentaCorriente = { saldo: number; movimientos: MovimientoCC[] }

/** La cuenta corriente de un cliente: `saldo` positivo es lo que DEBE, negativo lo que tiene a favor. */
export async function cuentaCorrienteDe(api: APIRequestContext, cliente: { id: number }): Promise<CuentaCorriente> {
  return json<CuentaCorriente>(await api.get(`/api/cuenta-corriente/${cliente.id}`, { maxRetries: 3 }), 'GET /api/cuenta-corriente/{id}')
}

/** Un pago a cuenta por la API; devuelve el id del recibo de cobranza. */
export async function pagarPorApi(
  api: APIRequestContext, cliente: { id: number }, monto: number, concepto = 'Pago e2e',
): Promise<{ recibo_id: number }> {
  return json(
    await api.post(`/api/cuenta-corriente/${cliente.id}/pagar`, {
      data: { monto, fecha: hoy(), concepto, medio_pago: 'efectivo', referencia: '' },
    }),
    'POST /api/cuenta-corriente/{id}/pagar',
  )
}

// ── Facturas ────────────────────────────────────────────────────────────────

export type Factura = {
  id: number; tipo: number; punto_venta: number; numero: number; total: number; cae: string | null; cliente_razon: string
}

/** Una Factura C por la API (el emisor de la instancia de prueba es monotributista: no hay otro tipo). Con `ENV=development` el CAE es simulado. */
export async function crearFactura(
  api: APIRequestContext,
  { cliente, descripcion = unico('Servicio e2e'), cantidad = 1, precio }: { cliente: { id: number }; descripcion?: string; cantidad?: number; precio: number },
): Promise<Factura> {
  return json<Factura>(
    await api.post('/api/facturas', {
      data: {
        tipo: 11, fecha: hoy(), client_id: cliente.id, tax_rate: 0.21, condicion_venta: 'Contado',
        items: [{ description: descripcion, qty: cantidad, unit_price: precio }],
      },
    }),
    'POST /api/facturas',
  )
}
