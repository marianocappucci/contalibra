// Cliente HTTP delgado sobre la API de Contalibra. Cookie de sesion
// (cl_session) manejada por el browser via `credentials: "include"` -- en
// dev el proxy de Vite (vite.config.ts) mantiene todo en el mismo origen
// (localhost:5173) para que la cookie funcione sin CORS; en produccion el
// build de este frontend se sirve desde el mismo proceso FastAPI (ver
// web/app.py), tambien mismo origen. Toda la API nueva vive bajo /api/.
//
// Nucleo (ApiError/api.get-post-put-del-postForm) migrado a libra-ui/
// api-client (paquete de frontend compartido, ver wiki/entities/
// libra-ui.md) -- este archivo re-exporta eso y mantiene los tipos de
// dominio propios de Contalibra.
export { ApiError, api } from 'libra-ui/api-client'

import type { OpcionSelect } from 'libra-ui/SelectBuscable'

// Dominio de facturacion: vive en libra-ui/facturas, compartido con el otro
// producto que emite comprobantes. Se re-exporta desde aca para que los
// archivos que ya lo importaban de este modulo sigan andando sin cambios
// (mismo patron que `cn` en lib/utils.ts).
export { MEDIOS_PAGO_LABELS } from 'libra-ui/facturas'
export type {
  BorradorDuplicado, Caja, Factura, FacturaDetalle, FacturaItem,
} from 'libra-ui/facturas'
// El `export type ... from` re-exporta pero NO trae el nombre al ambito de
// este modulo, y aca abajo hay tipos propios que usan `Factura`.
import type { Factura } from 'libra-ui/facturas'

export type User = {
  username: string
  nombre: string
  role: 'admin' | 'operador' | 'cajero'
  modulos: string[]
  empresa_nombre: string
  mp_pending_count: number
  comprobantes_pendientes_count: number
}

// Lo que otro producto de la familia dejó para facturar acá. El mecanismo vive
// en libracore (`comprobantes_pendientes`); ver
// wiki/analyses/libradesk-contalibra-puente-facturacion.md.
export type ComprobantePendienteItem = {
  description: string
  qty: number
  unit_price: number
  iva_rate: number
}

export type ComprobantePendiente = {
  id: number
  origen_producto: string
  origen_instancia: string
  origen_tipo: 'cuota_contrato' | 'incidencia' | 'remito' | 'presupuesto'
  origen_id: string
  cliente_id: number | null
  cliente_cuit: string
  cliente_razon: string
  cliente_domicilio: string
  periodo_desde: string
  periodo_hasta: string
  concepto: string
  condicion_venta: string
  observaciones: string
  items: ComprobantePendienteItem[]
  total: number
  estado: 'pendiente' | 'facturado' | 'descartado'
  factura_id: number | null
  motivo_descarte: string
  resuelto_at: string
  resuelto_por: string
  created_at: string
}

// El formulario de factura armado a partir de los pendientes elegidos. No trae
// `tipo` ni `punto_venta` a propósito: los decide el producto según la
// condición de IVA del emisor y del receptor.
export type PrefillComprobantes = {
  comprobantes_ids: number[]
  avisos: string[]
  concepto: number
  condicion_venta: string
  tax_rate: number
  client_id: number | null
  client_name: string
  client_cuit: string
  client_address: string
  fecha: string
  observations: string
  items: { description: string; qty: number; unit_price: number }[]
  fch_serv_desde: string
  fch_serv_hasta: string
  fch_vto_pago: string
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

export type AliasFacturacion = {
  id: number
  tipo: 'cuit' | 'email'
  valor: string
  cliente_id: number
}

export type ClienteConAlias = Cliente & {
  alias_facturacion: AliasFacturacion[]
  // Restaurado desde web/templates/clientes/detail.html -- ver GET
  // /api/clientes/{id} en web/api/clientes.py (auditoria campo por campo,
  // 2026-07-24). Los tipos Factura/Presupuesto/Remito ya existian, se
  // declaran mas abajo en este archivo (el orden no importa para types).
  facturas: Factura[]
  presupuestos: Presupuesto[]
  remitos: Remito[]
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
  tipo: 'producto' | 'servicio'
}

export const UNIDADES = ['u', 'kg', 'g', 'lt', 'ml', 'm', 'cm', 'm²', 'caja', 'par', 'docena', 'pack'] as const

export type CategoriaProducto = { id: number; nombre: string }

export type ConsultaCuit = {
  nombre?: string
  domicilio?: string
  iva_condition?: string
  estado?: string
  error?: string
}

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

/** Estado de la copia del backup en la nube del cliente (add-on).
 *
 * `contratado: false` es "no tenés el add-on", **no** una falla: la pantalla no
 * tiene que mostrar una alarma a quien no lo contrató. Y `al_dia: false` con
 * `contratado: true` sí es una alarma — puede ser que la última subida falló, o
 * que anduvo pero hace días. El backend distingue los casos en `motivo`. */
export type ResguardoExterno = {
  contratado: boolean
  al_dia: boolean | null
  motivo: string | null
  detalle: {
    cuando: string | null
    archivo: string | null
    destino: string | null
    bytes: number | null
    en_destino: number | null
    error: string | null
  } | null
}

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
  venta_id: number | null
  factura_id: number | null
}

// Recibo emitido (libracore >= v1.9.0). `numero_visible` viene armado del
// backend con el formato 0001-00000001 -- el front no lo compone, para que el
// numero del papel y el de la pantalla no puedan divergir.
export type Recibo = {
  id: number
  numero_visible: string
  fecha: string
  cliente_id: number | null
  cliente_razon: string
  cliente_cuit: string
  concepto: string
  origen_tipo: 'factura' | 'venta' | 'cc_pago'
  origen_id: number | null
  total: number
  anulado: boolean
  anulado_motivo: string
}

export const ORIGEN_RECIBO_LABELS: Record<string, string> = {
  factura: 'Factura',
  venta: 'Venta',
  cc_pago: 'Cuenta corriente',
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
  usuario_nombre: string | null
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
  remito_id: number | null
}

export type ProductoBusqueda = { id: number; codigo: string; nombre: string; precio_venta: number; unidad: string }


export type TipoFactura = { value: number; label: string }


export type Remito = {
  id: number
  number: string
  date: string
  client_id: number | null
  client_name: string
  client_address: string
  client_cuit: string
  client_email: string
  client_phone: string
  items: { description: string; qty: number }[]
  observations: string
  total: number
}

export type Presupuesto = {
  id: number
  number: string
  date: string
  valid_until: string
  status: string
  client_id: number | null
  client_name: string
  client_address: string
  client_cuit: string
  client_email: string
  client_phone: string
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
  payment_method: string | null
  descripcion_mp: string | null
  payer_id_type: string | null
  payer_id_number: string | null
  estado_factura: string
  factura_id: number | null
  created_at: string
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
  origen_banco: string | null
  origen_cbu: string | null
  payer_email: string
  payer_name: string
  payer_id_type: string | null
  payer_id_number: string
  estado_factura: string
  factura_id: number | null
  created_at: string
  cliente: Cliente | null
}

export type LibroIvaFactura = {
  id: number; tipo: number; punto_venta: number; numero: number; fecha: string
  cliente_razon: string; cliente_cuit: string; subtotal: number; iva_amount: number; total: number
  cae?: string
}
export type LibroIvaEgreso = {
  id: number; fecha: string; proveedor_nombre: string; numero: string
  monto_neto: number; iva_monto: number; total: number
  proveedor_cuit?: string; iva_pct?: number
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

export type CajaMedioVals = { ingresos: number; ingresos_ops: number; egresos: number; egresos_ops: number }
export type CajaMedioPivot = {
  id: number; nombre: string; medios: Record<string, CajaMedioVals>
  total_ingresos: number; total_egresos: number; saldo: number
}
export type CajaMediosData = {
  desde: string; hasta: string
  cajas_config: CajaConfig[]
  cajas: CajaMedioPivot[]
  totales: Record<string, CajaMedioVals>
  medio_label: Record<string, string>
}

export type LogActividad = {
  ts: string
  fecha: string
  tipo: string
  descripcion: string
  monto: number
  usuario: string
  turno_id: number | null
  // Confirmado presente en la respuesta real de db.get_actividad_log()
  // (inspeccionado en vivo en el contenedor del VPS, 2026-07-24) -- la
  // version Jinja2 vieja (git 1a8808c, web/templates/admin/logs.html) los
  // usaba para el link "Ver" por fila. Se dejan opcionales igual por si
  // algun registro viejo no los tuviera cargados.
  ref_tabla?: string | null
  ref_id?: number | null
}

export type LogAuth = { id: number; evento: string; username: string; ip: string; ts: string }

export type LogsData = {
  actividad: LogActividad[]
  tipo_meta: Record<string, { label: string; color: string }>
  total: number
  total_pages: number
  page: number
  usuarios: Usuario[]
  auth_log: LogAuth[]
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

// --- opciones para los selects con busqueda (libra-ui/SelectBuscable) ------
//
// Viven aca, junto a los tipos, para que las cuatro pantallas que eligen un
// cliente lo muestren y lo busquen igual. El `hint` no es decorativo: ademas
// de desambiguar dos clientes de nombre parecido, **entra en la busqueda**.
//
// En un sistema de facturacion el CUIT es el mejor discriminador: es lo que
// suele tenerse a mano del papel, y dos clientes pueden llamarse casi igual.

export function opcionesCliente(clientes: Cliente[]): OpcionSelect[] {
  return clientes.map((c) => ({
    value: String(c.id),
    label: c.name,
    hint: [c.cuit_dni, c.activo ? null : 'inactivo'].filter(Boolean).join(' · ') || undefined,
  }))
}

export function opcionesProveedor(proveedores: Proveedor[]): OpcionSelect[] {
  return proveedores.map((p) => ({
    value: String(p.id),
    label: p.nombre,
    hint: p.cuit_dni || undefined,
  }))
}

// Tipado estructural y no : Stock.tsx trabaja con ,
// que trae los mismos cuatro campos sin ser el mismo tipo.
export function opcionesProducto(
  productos: { id: number; nombre: string; codigo?: string | null; categoria?: string }[],
): OpcionSelect[] {
  return productos.map((p) => ({
    value: String(p.id),
    // El codigo es lo que se tipea cuando se lo sabe de memoria, y lo que
    // esta impreso en la etiqueta o en la lista de precios del proveedor.
    label: p.nombre,
    hint: [p.codigo, p.categoria].filter(Boolean).join(' · ') || undefined,
  }))
}
