// Cliente HTTP delgado sobre la API de Contalibra. Cookie de sesion
// (cl_session) manejada por el browser via `credentials: "include"` -- en
// dev el proxy de Vite (vite.config.ts) mantiene todo en el mismo origen
// (localhost:5173) para que la cookie funcione sin CORS; en produccion el
// build de este frontend se sirve desde el mismo proceso FastAPI (ver
// web/app.py), tambien mismo origen. Toda la API nueva vive bajo /api/.

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: 'include',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (response.status === 204) {
    return undefined as T
  }

  const isJson = response.headers.get('content-type')?.includes('application/json')
  const data = isJson ? await response.json() : undefined

  if (!response.ok) {
    const detail = (data && typeof data === 'object' && 'detail' in data)
      ? String((data as { detail: unknown }).detail)
      : response.statusText
    throw new ApiError(response.status, detail)
  }

  return data as T
}

async function requestForm<T>(method: string, path: string, form: FormData): Promise<T> {
  const response = await fetch(path, { method, credentials: 'include', body: form })
  const isJson = response.headers.get('content-type')?.includes('application/json')
  const data = isJson ? await response.json() : undefined
  if (!response.ok) {
    const detail = (data && typeof data === 'object' && 'detail' in data)
      ? String((data as { detail: unknown }).detail)
      : response.statusText
    throw new ApiError(response.status, detail)
  }
  return data as T
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
  // Uploads (logo, certificados ARCA, restore de DB) -- multipart, sin
  // Content-Type explicito para que el browser agregue el boundary.
  postForm: <T>(path: string, form: FormData) => requestForm<T>('POST', path, form),
}

export type User = {
  username: string
  nombre: string
  role: 'admin' | 'operador' | 'cajero'
  modulos: string[]
}

export type FacturaSinCobrar = {
  id: number
  tipo: number
  punto_venta: number
  numero: number
  fecha: string
  cliente_razon: string
  total: number
  letra: string
  label_numero: string
}

export type PresupuestoPendiente = {
  id: number
  number: string
  date: string
  client_name: string
  total: number
}

export type MovimientoCaja = {
  id: number
  fecha: string
  tipo: string
  concepto: string
  monto: number
  referencia: string
  factura_id: number | null
  medio_pago: string
}

export type Cliente = {
  id: number
  name: string
  address: string
  cuit_dni: string
  email: string
  phone: string
  iva_condition: string
  auto_facturar: number
  activo: number
}

export const IVA_CONDITIONS = [
  'Responsable Inscripto',
  'Monotributista',
  'IVA Exento',
  'Consumidor Final',
  'No Alcanzado',
  'IVA No Responsable',
] as const

export type Producto = {
  id: number
  codigo: string | null
  nombre: string
  descripcion: string
  precio_venta: number
  precio_costo: number
  unidad: string
  categoria: string
  stock_minimo: number
  estacion: string
  vendible: number
  activo: number
}

export const UNIDADES = ['u', 'kg', 'g', 'lt', 'ml', 'm', 'cm', 'm²', 'caja', 'par', 'docena', 'pack'] as const

export type ListaPrecio = {
  id: number
  nombre: string
  descripcion: string
  activa: number
  es_default: number
}

export type ItemListaPrecio = {
  id: number
  codigo: string | null
  nombre: string
  unidad: string
  categoria: string
  precio_venta: number
  precio_costo: number
  precio_lista: number
  en_lista: number
}

export type Proveedor = {
  id: number
  nombre: string
  cuit_dni: string
  email: string
  phone: string
  address: string
  iva_condition: string
}

export type Egreso = {
  id: number
  fecha: string
  proveedor_id: number | null
  proveedor_nombre: string
  tipo_comprobante: string
  numero: string
  categoria: string
  concepto: string
  monto_neto: number
  iva_pct: number
  iva_monto: number
  total: number
  estado: 'pendiente' | 'parcial' | 'pagado'
  observaciones: string
}

export type ResumenEgresos = {
  total_periodo: number
  pagado: number
  pendiente: number
}

export type CategoriaEgreso = { id: number; nombre: string }

export type PagoEgreso = {
  id: number
  egreso_id: number
  fecha: string
  monto: number
  caja_id: number | null
  medio_pago: string
  referencia: string
}

export type Caja = {
  id: number
  nombre: string
  es_default: number
  medios_pago: string[]
}

export const MEDIOS_PAGO_LABELS: Record<string, string> = {
  efectivo: 'Efectivo',
  transferencia: 'Transferencia',
  mercadopago: 'Mercado Pago',
  cuenta_dni: 'Cuenta DNI',
  billetera: 'Otras billeteras',
  cuenta_corriente: 'Cuenta corriente',
}

export const TIPOS_COMPROBANTE = [
  { id: 'factura', label: 'Factura' },
  { id: 'ticket', label: 'Ticket / Recibo' },
  { id: 'recibo', label: 'Recibo oficial' },
  { id: 'otro', label: 'Otro' },
] as const

export type Usuario = {
  id: number
  username: string
  nombre: string
  email: string
  role: 'admin' | 'operador' | 'cajero'
  activo: number
}

export const ROLES = [
  { value: 'admin', label: 'Admin' },
  { value: 'operador', label: 'Operador' },
  { value: 'cajero', label: 'Cajero' },
] as const

export type ConfigCfg = {
  servicio_estado: 'activo' | 'pausado' | 'suspendido'
  servicio_mensaje: string
  empresa_nombre: string
  empresa_direccion: string
  empresa_cuit: string
  empresa_telefono: string
  empresa_email: string
  empresa_iibb: string
  empresa_iva_condition: string
  empresa_inicio_actividades: string
  logo_path: string
  mp_access_token: string
  mp_webhook_secret: string
  mp_concepto_descripcion: string
  mp_iva_rate: string
  mp_user_id: string
  mp_pos_id: string
  email_smtp_host: string
  email_smtp_port: string
  email_smtp_user: string
  email_smtp_password: string
  email_from: string
  email_from_name: string
  ticket_ancho_mm: string
  ticket_fuente_size: string
  ticket_mostrar_logo: string
  ticket_linea_corte: string
  ticket_pie: string
}

export type ArcaConfig = {
  empresa: string
  cuit: string
  punto_venta: number
  ambiente: string
  alias: string
  clave_path: string
  certificado_path: string
}

export type ConfigData = { cfg: ConfigCfg; arca: ArcaConfig | Record<string, never> }

export type Backup = { filename: string; size_mb: number; mtime: string }

export type Deposito = {
  id: number
  nombre: string
  descripcion: string
  es_default: number
  activo: number
  total_productos?: number
}

export type StockItem = {
  id: number
  codigo: string | null
  nombre: string
  unidad: string
  categoria: string
  stock_minimo: number
  activo: number
  stock_actual: number
}

export type MovimientoStock = {
  id: number
  producto_id: number
  producto_nombre: string
  unidad: string
  tipo: string
  cantidad: number
  referencia: string
  fecha: string
}

export type StockPorDeposito = { id: number; nombre: string; es_default: number; stock_actual: number }

export type ClienteConSaldoCC = { id: number; name: string; cuit_dni: string; saldo: number }

export type MovimientoCC = {
  fecha: string
  tipo: 'debito' | 'credito'
  concepto: string
  monto: number
  referencia: string
  medio: string
  cc_pago_id: number | null
  usuario_nombre: string | null
}

export type CuentaTesoreria = {
  id: number
  nombre: string
  tipo: string
  banco: string
  numero: string
  descripcion: string
  saldo_inicial: number
  saldo: number
  activa: number
}

export type MovimientoTesoreria = {
  id: number
  fecha: string
  cuenta_id: number
  cuenta_nombre: string
  cuenta_destino_id: number | null
  cuenta_destino_nombre: string | null
  tipo: string
  monto: number
  concepto: string
  referencia: string
  transferencia_id: number | null
}

export const TIPOS_CUENTA_TESORERIA = [
  { value: 'banco', label: 'Banco' },
  { value: 'efectivo', label: 'Efectivo' },
  { value: 'digital', label: 'Billetera digital' },
  { value: 'otro', label: 'Otro' },
] as const

export type CajaMovimiento = {
  id: number
  fecha: string
  tipo: string
  concepto: string
  monto: number
  referencia: string
  factura_id: number | null
  caja_id: number | null
  caja_nombre: string | null
  usuario_nombre: string | null
  medio_pago: string
}

export type ResumenCaja = { ingresos: number; egresos: number; saldo_periodo: number; saldo_total: number }

export type CajaConfig = {
  id: number
  nombre: string
  descripcion: string
  medios_pago: string[]
  es_default: number
  activo: number
}

export type Turno = {
  id: number
  usuario_id: number
  usuario_nombre: string
  apertura: string
  cierre: string | null
  monto_inicial: number
  monto_declarado_cierre: number | null
  monto_esperado_cierre: number | null
  estado: 'abierto' | 'cerrado'
  notas: string
}

export type ResumenTurno = {
  ventas: { id: number; numero: string; fecha: string; cliente_nombre: string; total: number; estado: string }[]
  pagos_por_medio: Record<string, number>
  total_ventas: number
  efectivo_ventas: number
}

export type VentaItem = { nombre: string; qty: number; precio: number; subtotal: number; producto_id: number | null }
export type VentaPago = { id?: number; medio: string; monto: number; referencia: string }

export type Venta = {
  id: number
  numero: string
  fecha: string
  items: VentaItem[]
  subtotal: number
  descuento: number
  total: number
  cliente_id: number | null
  cliente_nombre: string
  observaciones: string
  estado: 'pendiente' | 'parcial' | 'cobrada' | 'anulada'
  pagos: VentaPago[]
  factura_id: number | null
  factura_display: string | null
}

export type ProductoBusqueda = { id: number; codigo: string; nombre: string; precio_venta: number; unidad: string }

export type FacturaItem = { description: string; qty: number; unit_price: number; subtotal: number }

export type Factura = {
  id: number
  tipo: number
  punto_venta: number
  numero: number
  fecha: string
  cliente_cuit: string
  cliente_razon: string
  items: FacturaItem[]
  subtotal: number
  iva_amount: number
  total: number
  concepto: number
  cae: string
  cae_vto: string
  observaciones: string
  condicion_venta: string
  total_cobrado?: number
}

export type FacturaDetalle = {
  factura: Factura
  tipo_label: string
  concepto_label: string
  iva_label: string
  notas_credito: Factura[]
  notas_debito: Factura[]
  factura_original: Factura | null
  cobros: { id: number; monto: number; medio_pago: string; fecha: string; referencia: string }[]
  total_cobrado: number
  pendiente: number
  cliente_email: string
}

export type TipoFactura = { value: number; label: string }

export type Remito = {
  id: number
  number: string
  date: string
  client_id: number | null
  client_name: string
  items: { description: string; qty: number }[]
  observations: string
}

export type Presupuesto = {
  id: number
  number: string
  date: string
  valid_until: string
  status: string
  client_id: number | null
  client_name: string
  items: { description: string; qty: number; unit_price: number; subtotal: number }[]
  subtotal: number
  tax_rate: number
  tax_amount: number
  total: number
  observations: string
  remito_id: number | null
}

export const ESTADOS_PRESUPUESTO = ['borrador', 'enviado', 'aceptado', 'rechazado', 'vencido', 'facturado'] as const

export type MpPago = {
  id: number
  mp_payment_id: string
  monto: number
  payer_email: string
  payer_name: string
  payment_type: string | null
  payer_id_number: string | null
  estado_factura: string
  cliente: Cliente | null
}

export type MpMovimiento = {
  id: number
  mp_movement_id: string
  tipo: string
  monto: number
  fecha: string
  descripcion: string
  origen_nombre: string
  payer_email: string
  payer_name: string
  payer_id_number: string
  estado_factura: string
  cliente: Cliente | null
}

export type LibroIvaFactura = {
  id: number; tipo: number; punto_venta: number; numero: number; fecha: string
  cliente_razon: string; cliente_cuit: string; subtotal: number; iva_amount: number; total: number
}
export type LibroIvaEgreso = {
  id: number; fecha: string; proveedor_nombre: string; numero: string
  monto_neto: number; iva_monto: number; total: number
}
export type ResumenIva = {
  cbtes: number; neto: number; iva: number; total: number
  por_tasa: Record<string, { neto: number; iva: number; cbtes: number }>
}
export type LibrosIvaData = {
  desde: string; hasta: string; empresa_cuit: string
  facturas: LibroIvaFactura[]; egresos: LibroIvaEgreso[]
  resumen_v: ResumenIva; resumen_c: ResumenIva
}

export type ReporteResumen = {
  ventas_cantidad: number; ventas_total: number; facturas_cantidad: number; caja_saldo: number
}
export type ReporteVentaTs = { periodo: string; cantidad: number; total: number }
export type ReporteMedio = { medio: string; operaciones: number; total: number }
export type ReporteProducto = { nombre: string; cantidad: number; total: number }
export type ReporteCaja = { tipo: string; cantidad: number; total: number }
export type ReporteStockBajo = { id: number; nombre: string; codigo: string | null; stock_actual: number; stock_minimo: number }
export type ReportesData = {
  desde: string; hasta: string; agrupacion: string
  resumen: ReporteResumen; ventas_ts: ReporteVentaTs[]; medios: ReporteMedio[]
  productos: ReporteProducto[]; caja: ReporteCaja[]; stock_bajo: ReporteStockBajo[]
}

export type DashboardData = {
  mes_desde: string
  mes_hasta: string
  facturado_mes: number
  cobrado_mes: number
  egresos_mes: number
  saldo_total: number
  cant_facturas_mes: number
  facturas_sin_cobrar: FacturaSinCobrar[]
  presupuestos_pendientes: PresupuestoPendiente[]
  ultimos_movimientos: MovimientoCaja[]
}
