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


// Dominio de facturacion: vive en libra-ui/facturas, compartido con el otro
// producto que emite comprobantes. Se re-exporta desde aca para que los
// archivos que ya lo importaban de este modulo sigan andando sin cambios
// (mismo patron que `cn` en lib/utils.ts).
// MEDIOS_PAGO_LABELS se fue: era una copia de la lista del motor y divergia en
// las dos direcciones. La lista sale de la API; las etiquetas y abreviaturas,
// de 'libra-ui/medios-pago'. Ver lib/medios-pago.ts.
// Los tipos y helpers del catalogo, el stock y los depositos viven en el kit
// desde P9-M1 (2026-09-06): son el contrato JSON de las factories de
// LibraCommerce, el mismo para los dos productos. Se re-exportan con los
// nombres historicos para que el resto de las pantallas no cambie un import.
export { UNIDADES, TIPO_MOVIMIENTO_LABELS, opcionesProducto } from 'libra-ui/comercio/tipos'
export type {
  Producto, CategoriaProducto, Deposito, StockItem, StockListado, MovimientoStock, StockPorDeposito,
} from 'libra-ui/comercio/tipos'
export type { ListaPrecio, ItemListaPrecio, Quiebre, ProductoBusqueda } from 'libra-ui/comercio/tipos'
export type {
  Venta, VentaItem, VentaPago, Turno, ResumenTurno, CajaConfig, CajaMovimiento, ResumenCaja,
} from 'libra-ui/comercio/tipos'
export { opcionesCliente } from 'libra-ui/comercio/tipos'
export type {
  AliasFacturacion, ClienteConAlias, Proveedor, Egreso, ResumenEgresos, CategoriaEgreso, PagoEgreso,
  ClienteConSaldoCC, MovimientoCC, CuentaTesoreria, MovimientoTesoreria,
  LibroIvaFactura, LibroIvaEgreso, ResumenIva, LibrosIvaData,
  ReporteResumen, ReporteVentaTs, ReporteMedio, ReporteProducto, ReporteCaja, ReporteStockBajo, ReportesData,
  CajaMedioVals, CajaMedioPivot, CajaMediosData, LogActividad, LogAuth, LogsData,
} from 'libra-ui/comercio/tipos'
export {
  TIPOS_COMPROBANTE, TIPOS_CUENTA_TESORERIA, opcionesProveedor, opcionesCategoriaPorNombre,
} from 'libra-ui/comercio/tipos'

export type {
  BorradorDuplicado, Caja, Factura, FacturaDetalle, FacturaItem,
} from 'libra-ui/facturas'
// El `export type ... from` re-exporta pero NO trae el nombre al ambito de
// este modulo, y aca abajo hay tipos propios que usan `Factura`.

// La bandeja de MercadoPago: sus tipos viven en `libra-ui/mp` desde la v0.45.0,
// junto a la pantalla que los muestra. Estaban declarados acá y, palabra por
// palabra, también en el otro producto.
//
// 🔑 El `export type ... from` re-exporta pero NO trae el nombre al ámbito de
// este módulo, y acá abajo hay tipos propios que usan `Cliente` — de ahí el
// `import type` de al lado. Mismo cuidado que con `Factura`.
export type { Cliente, MpMovimiento, MpPago } from 'libra-ui/mp'

// La lista de condiciones frente al IVA la fija ARCA, no el producto: vive en
// `libra-ui/facturas` desde la v0.45.0. Estaba escrita idéntica en los dos
// productos, y una lista fiscal que diverge es cómo un cliente termina cargado
// con una condición que una instancia acepta y la otra no.
export { IVA_CONDITIONS } from 'libra-ui/facturas'


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






export type ConsultaCuit = {
  nombre?: string
  domicilio?: string
  iva_condition?: string
  estado?: string
  error?: string
}










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

// `GET /api/config` sigue devolviendo `servicio_estado` y `servicio_mensaje`
// —viven en el mismo `config.json`—, pero no se declaran acá a propósito: no
// son configuración del cliente. El corte de servicio se administra desde el
// backoffice de superadmin. Declararlos invita a volver a ponerles un
// formulario encima.
export type ConfigCfg = {
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
  mp_auto_facturar_ventas: boolean
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
  /** Si el archivo esta realmente en el volumen, no solo si hay un path
   *  guardado: un path que apunta a un archivo que ya no esta se lee igual. */
  tiene_certificado?: boolean
  tiene_clave?: boolean
}

/** `GET /api/config/arca/estado`.
 *
 *  🔑 `dias_para_vencer` es el dato que evita la falla silenciosa: los
 *  certificados de ARCA duran dos anos y el dia que vencen la facturacion deja
 *  de andar sin que nadie haya tocado nada. */
export type ArcaEstado = {
  configurado: boolean
  ambiente: string
  cuit: string
  tiene_certificado: boolean
  tiene_clave: boolean
  vence?: string
  dias_para_vencer?: number
  vencido?: boolean
  sujeto?: string
  error_certificado?: string
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



// Tipado estructural y no : Stock.tsx trabaja con ,
// que trae los mismos cuatro campos sin ser el mismo tipo.
