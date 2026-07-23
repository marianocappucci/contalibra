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

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
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
