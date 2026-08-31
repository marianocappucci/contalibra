import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, IVA_CONDITIONS,
  type Cliente, type ListaPrecio, type ProductoBusqueda, type Venta,
  opcionesCliente,
} from '../api'
import { useMediosPago } from '../lib/medios-pago'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { BadgeEstado, type TonoEstado } from 'libra-ui/badge-estado'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger, DialogClose,
} from '@/components/ui/dialog'
import { anchoColumnaAcciones, DataTable, sortableHeader } from 'libra-ui/data-table'
import { SelectBuscable } from 'libra-ui/SelectBuscable'
import {
  ShoppingCart, Plus, Printer, FileCheck, Ban, ReceiptText, ListChecks, UserPlus, X, CheckCircle2,
} from 'lucide-react'
import { TituloPantalla } from 'libra-ui/titulo-pantalla'
import { hoyISO } from 'libra-ui/fechas'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

// El tono conserva el significado que la pantalla ya le daba a cada estado:
// lo que cambia es como se pinta, no que quiere decir.
const ESTADO_TONO: Record<string, TonoEstado> = {
  cobrada: 'ok', parcial: 'atencion', pendiente: 'neutro', anulada: 'negativo',
}

const ESTADO_LABELS: Record<string, string> = {
  cobrada: 'Cobrada', parcial: 'Pago parcial', pendiente: 'Pendiente', anulada: 'Anulada',
}
function estadoLabel(estado: string): string {
  return ESTADO_LABELS[estado] ?? estado
}

// 🔴 Acá había un `MEDIOS_PAGO_SHORT` propio: **la novena copia** del
// vocabulario en este repo, y le faltaban las tarjetas. Las abreviaturas sí son
// una decisión de pantalla —"Tarjeta de débito" no entra en esta columna— pero
// viven en `libra-ui/medios-pago`, compartidas con Restolibra, y son un lookup
// PARCIAL con fallback: un medio nuevo en LibraCore aparece con su nombre
// completo en vez de romper la grilla.
//
// El detalle de la venta (un click en la fila) muestra el desglose completo con
// el label largo y el monto por medio.

type ItemRow = { nombre: string; qty: string; precio: string; producto_id: number | null }
//: `tocado` marca que el cajero escribió el monto a mano. Mientras esté en
//  false la fila se autocompleta con lo que falta cubrir, así el caso normal
//  —un solo medio por el total— no obliga a tipear el importe, y el pago
//  dividido sigue mandando en cuanto alguien lo escribe.
//: `cobrarConQr` es la diferencia entre "el cliente ya me transfirió" y "le voy
//  a cobrar con el QR ahora". Las dos se cargan como `mercadopago`, y sin esto
//  el backend no puede distinguirlas: la venta nacería cobrada y sumando al
//  arqueo **antes de que nadie escanee nada**.
type PagoRow = {
  medio: string; monto: string; referencia: string; tocado: boolean
  cobrarConQr: boolean
}

const EMPTY_ITEM: ItemRow = { nombre: '', qty: '1', precio: '0', producto_id: null }
const EMPTY_PAGO: PagoRow = {
  medio: 'efectivo', monto: '', referencia: '', tocado: false, cobrarConQr: false,
}

/** El medio con el que cobra el QR de caja. El backend **rechaza**
 *  `cobrar_con_qr` en cualquier otro medio —dejaría la venta pendiente para
 *  siempre, porque nada la acreditaría—, así que el check sólo aparece acá. */
const MEDIO_DEL_QR = 'mercadopago'


/** Input de importe, con el `$` adentro y pegado a la izquierda. */
function MoneyInput({ value, onChange, className = '', placeholder }: {
  value: string
  onChange: (v: string) => void
  className?: string
  placeholder?: string
}) {
  return (
    <div className={`relative ${className}`}>
      <span className="pointer-events-none absolute inset-y-0 left-2.5 flex items-center text-sm text-muted-foreground">$</span>
      <Input
        type="number" step="0.01" value={value} placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="pl-6"
      />
    </div>
  )
}

export function Ventas() {
  const { medios, etiquetaCorta: etiquetaCortaDeMedio } = useMediosPago()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [ventas, setVentas] = useState<Venta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState('todas')
  const [q, setQ] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')

  const [showNueva, setShowNueva] = useState(false)
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [listasPrecio, setListasPrecio] = useState<ListaPrecio[]>([])
  const [items, setItems] = useState<ItemRow[]>([{ ...EMPTY_ITEM }])
  const [pagos, setPagos] = useState<PagoRow[]>([{ ...EMPTY_PAGO }])
  const [clienteId, setClienteId] = useState('')
  const [listaPrecioId, setListaPrecioId] = useState('')
  const [descuento, setDescuento] = useState('0')
  const [observaciones, setObservaciones] = useState('')
  const [savingVenta, setSavingVenta] = useState(false)
  const [sugerencias, setSugerencias] = useState<{ index: number; items: ProductoBusqueda[] } | null>(null)

  const [nuevoCliente, setNuevoCliente] = useState(false)
  const [ncNombre, setNcNombre] = useState('')
  const [ncCuit, setNcCuit] = useState('')
  const [ncIva, setNcIva] = useState('')
  const [ncEmail, setNcEmail] = useState('')
  const [ncPhone, setNcPhone] = useState('')
  const [ncSaving, setNcSaving] = useState(false)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ tab })
      if (q) params.set('q', q)
      if (desde) params.set('desde', desde)
      if (hasta) params.set('hasta', hasta)
      setVentas(await api.get<Venta[]>(`/api/ventas?${params.toString()}`))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function limpiarFiltros() {
    setQ(''); setDesde(''); setHasta('')
    setTimeout(load, 0)
  }

  async function anular(venta: Venta) {
    setError(null)
    try {
      await api.post(`/api/ventas/${venta.id}/anular`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  function abrirNueva() {
    setItems([{ ...EMPTY_ITEM }])
    setPagos([{ ...EMPTY_PAGO }])
    setClienteId(''); setListaPrecioId(''); setDescuento('0'); setObservaciones('')
    setNuevoCliente(false)
    setNcNombre(''); setNcCuit(''); setNcIva(''); setNcEmail(''); setNcPhone('')
    setSugerencias(null)
    setError(null)
    api.get<Cliente[]>('/api/clientes').then((c) => setClientes(c.filter((x) => x.activo))).catch(() => {})
    api.get<ListaPrecio[]>('/api/listas-precio').then(setListasPrecio).catch(() => {})
    setShowNueva(true)
  }

  async function buscarProducto(index: number, texto: string) {
    updateItem(index, 'nombre', texto)
    if (texto.trim().length < 2) {
      setSugerencias(null)
      return
    }
    try {
      const lp = listaPrecioId ? `&lista_id=${listaPrecioId}` : ''
      const res = await api.get<ProductoBusqueda[]>(`/productos/buscar?q=${encodeURIComponent(texto)}${lp}`)
      setSugerencias({ index, items: res })
    } catch {
      setSugerencias(null)
    }
  }

  function elegirProducto(index: number, p: ProductoBusqueda) {
    setItems((rows) => rows.map((r, i) => i === index ? { nombre: p.nombre, qty: r.qty || '1', precio: String(p.precio_venta), producto_id: p.id } : r))
    setSugerencias(null)
  }

  function updateItem(index: number, field: keyof ItemRow, value: string) {
    setItems((rows) => rows.map((r, i) => i === index ? { ...r, [field]: value, ...(field === 'nombre' ? { producto_id: null } : {}) } : r))
  }

  function addItemRow() {
    setItems((rows) => [...rows, { ...EMPTY_ITEM }])
  }

  function removeItemRow(index: number) {
    setItems((rows) => rows.filter((_, i) => i !== index))
  }

  function updatePago(index: number, field: 'medio' | 'referencia', value: string) {
    setPagos((rows) => rows.map((r, i) => {
      if (i !== index) return r
      const fila = { ...r, [field]: value }
      // 🔴 Cambiar de medio apaga el check. Si quedara prendido sobre
      // `efectivo`, el backend rebota con 422 al guardar —con el mostrador
      // esperando— y si además lo dejáramos pasar, la venta quedaría pendiente
      // para siempre: nada acredita un pago en efectivo.
      if (field === 'medio' && value !== MEDIO_DEL_QR) fila.cobrarConQr = false
      return fila
    }))
  }

  function updatePagoQr(index: number, valor: boolean) {
    setPagos((rows) => rows.map((r, i) => i === index ? { ...r, cobrarConQr: valor } : r))
  }

  /** El monto escrito a mano manda: la fila deja de autocompletarse. */
  function updateMontoPago(index: number, value: string) {
    setPagos((rows) => rows.map((r, i) => i === index ? { ...r, monto: value, tocado: true } : r))
  }

  function addPagoRow() {
    setPagos((rows) => [...rows, { ...EMPTY_PAGO }])
  }

  function removePagoRow(index: number) {
    setPagos((rows) => rows.filter((_, i) => i !== index))
  }

  const subtotalCalc = items.reduce((acc, r) => acc + (Number(r.qty) || 0) * (Number(r.precio) || 0), 0)
  const totalCalc = Math.max(0, subtotalCalc - (Number(descuento) || 0))

  // Lo que falta cubrir sin contar las filas que todavía se autocompletan.
  const cubiertoAMano = pagos.reduce((acc, p) => acc + (p.tocado ? Number(p.monto) || 0 : 0), 0)
  const sugerido = Math.round(Math.max(0, totalCalc - cubiertoAMano) * 100) / 100

  //: El importe efectivo de cada fila: el escrito, o el sugerido si nadie la tocó.
  //  Se reparte entre las filas sin tocar poniéndolo en la primera, para que dos
  //  filas vacías no sumen el total dos veces.
  const primeraSinTocar = pagos.findIndex((p) => !p.tocado)
  const montoDeFila = (row: PagoRow, i: number): string =>
    row.tocado ? row.monto : (i === primeraSinTocar && sugerido > 0 ? String(sugerido) : '')

  const pagadoCalc = pagos.reduce((acc, p, i) => acc + (Number(montoDeFila(p, i)) || 0), 0)
  const difCalc = Math.round((totalCalc - pagadoCalc) * 100) / 100

  async function crearVenta() {
    setSavingVenta(true)
    setError(null)
    try {
      const venta = await api.post<Venta>('/api/ventas', {
        fecha: hoyISO(),
        items: items.filter((r) => r.nombre.trim() && Number(r.qty) > 0).map((r) => ({
          nombre: r.nombre, qty: Number(r.qty), precio: Number(r.precio) || 0, producto_id: r.producto_id,
        })),
        descuento: Number(descuento) || 0,
        cliente_id: clienteId ? Number(clienteId) : null,
        observaciones,
        // `montoDeFila` y no `p.monto`: la fila que nadie tocó lleva el importe
        // sugerido, que es lo que el cajero está viendo en pantalla. Mandar
        // `p.monto` dejaría la venta sin pagos aunque la pantalla dijera otra cosa.
        pagos: pagos
          .map((p, i) => ({
            medio: p.medio, monto: Number(montoDeFila(p, i)) || 0, referencia: p.referencia,
            // Sólo va en el medio del QR: el backend rechaza el resto, y
            // mandarlo en `efectivo` por una fila que cambió de medio con el
            // check puesto dejaría la venta pendiente para siempre.
            cobrar_con_qr: p.medio === MEDIO_DEL_QR && p.cobrarConQr,
          }))
          .filter((p) => p.monto > 0),
      })
      setShowNueva(false)
      navigate(`/ventas/${venta.id}`)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSavingVenta(false)
    }
  }

  async function crearClienteRapido() {
    if (!ncNombre.trim()) return
    setNcSaving(true)
    setError(null)
    try {
      const nuevo = await api.post<Cliente>('/api/clientes', {
        name: ncNombre.trim(), cuit_dni: ncCuit.trim(), iva_condition: ncIva, email: ncEmail.trim(), phone: ncPhone.trim(),
      })
      setClientes((prev) => [...prev, nuevo])
      setClienteId(String(nuevo.id))
      setNuevoCliente(false)
      setNcNombre(''); setNcCuit(''); setNcIva(''); setNcEmail(''); setNcPhone('')
    } catch (err) {
      setError(describeError(err))
    } finally {
      setNcSaving(false)
    }
  }

  const columns = useMemo<ColumnDef<Venta>[]>(() => [
    { accessorKey: 'numero', header: sortableHeader('N°'), size: 100, minSize: 90, cell: ({ row }) => <span className="block truncate font-mono text-sm font-semibold text-primary" title={row.original.numero}>{row.original.numero}</span> },
    { accessorKey: 'fecha', header: 'Fecha', size: 100, minSize: 90 },
    {
      id: 'pagos',
      header: 'Medios de pago',
      size: 150,
      minSize: 90,
      meta: { stretch: true },
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.pagos.length === 0
            ? <span className="text-muted-foreground">—</span>
            : row.original.pagos.map((p, i) => (
              <Badge key={i} variant="outline" className="font-normal">{etiquetaCortaDeMedio(p.medio)}</Badge>
            ))}
        </div>
      ),
    },
    { accessorKey: 'total', header: 'Total', size: 100, minSize: 80, cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.total)}</span> },
    {
      accessorKey: 'estado',
      header: 'Estado',
      size: 110,
      minSize: 90,
      cell: ({ row }) => <BadgeEstado tono={ESTADO_TONO[row.original.estado] ?? 'neutro'}>{estadoLabel(row.original.estado)}</BadgeEstado>,
    },
    {
      id: 'factura',
      header: 'Factura',
      size: 140,
      minSize: 100,
      cell: ({ row }) => row.original.factura_display
        ? <a href={`/facturas/${row.original.factura_id}`} className="inline-flex w-full items-center gap-1 truncate text-sm font-medium text-emerald-600 hover:underline dark:text-emerald-400" title={row.original.factura_display}><ReceiptText className="size-3.5 shrink-0" /><span className="truncate">{row.original.factura_display}</span></a>
        : row.original.estado !== 'anulada'
          ? <BadgeEstado tono="atencion">Sin facturar</BadgeEstado>
          : <span className="text-muted-foreground">—</span>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      size: anchoColumnaAcciones(3),
      minSize: anchoColumnaAcciones(3),
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          <Button asChild size="icon" variant="outline" title="Imprimir ticket"><a href={`/ventas/${row.original.id}/ticket`} target="_blank" rel="noreferrer" aria-label="Imprimir ticket"><Printer /></a></Button>
          {row.original.pagos.length > 0 && (
            <Button asChild size="icon" variant="outline" title="Ver recibo"><a href={`/ventas/${row.original.id}/recibo`} target="_blank" rel="noreferrer" aria-label="Ver recibo"><FileCheck /></a></Button>
          )}
          {user?.role === 'admin' && row.original.estado !== 'anulada' && (
            <Button size="icon" variant="outline" title="Anular" onClick={() => anular(row.original)}><Ban /></Button>
          )}
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [user])

  const emptyMessage = tab === 'sin_facturar'
    ? 'No hay ventas pendientes de facturar.'
    : tab === 'facturadas'
      ? 'No hay ventas facturadas aún.'
      : 'No hay ventas registradas aún.'

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <TituloPantalla icono={ShoppingCart}>Ventas</TituloPantalla>
        <Dialog open={showNueva} onOpenChange={setShowNueva}>
          <DialogTrigger asChild>
            <Button onClick={abrirNueva}><Plus />Nueva venta</Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2"><ShoppingCart className="size-4" />Nueva venta</DialogTitle>
            </DialogHeader>

            <div className="grid gap-4">
              <div className="flex flex-wrap items-end gap-3">
                <div className="grid gap-2">
                  <Label>Cliente</Label>
                  <div className="flex items-center gap-1">
                    <SelectBuscable
                      value={clienteId}
                      onChange={setClienteId}
                      opciones={opcionesCliente(clientes)}
                      placeholder="Consumidor Final"
                      ariaLabel="Cliente"
                      className="w-52"
                    />
                    <Button type="button" size="icon" variant="outline" title="Agregar nuevo cliente" onClick={() => setNuevoCliente((v) => !v)}>
                      <UserPlus />
                    </Button>
                  </div>
                </div>
                {listasPrecio.length > 0 && (
                  <div className="grid gap-2">
                    <Label>Lista de precios</Label>
                    <Select value={listaPrecioId || '__base__'} onValueChange={(v) => setListaPrecioId(v === '__base__' ? '' : v)}>
                      <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__base__">— Precio de venta —</SelectItem>
                        {listasPrecio.map((l) => <SelectItem key={l.id} value={String(l.id)}>{l.nombre}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div className="grid gap-2"><Label>Observaciones</Label><Input value={observaciones} onChange={(e) => setObservaciones(e.target.value)} className="w-64" /></div>
              </div>

              {nuevoCliente && (
                <div className="flex flex-wrap items-end gap-3 rounded-md border bg-muted/30 p-3">
                  <div className="grid gap-2"><Label>Nombre *</Label><Input value={ncNombre} onChange={(e) => setNcNombre(e.target.value)} className="w-44" /></div>
                  <div className="grid gap-2"><Label>CUIT/DNI</Label><Input value={ncCuit} onChange={(e) => setNcCuit(e.target.value)} className="w-32" /></div>
                  <div className="grid gap-2">
                    <Label>Condición IVA</Label>
                    <Select value={ncIva || '__none__'} onValueChange={(v) => setNcIva(v === '__none__' ? '' : v)}>
                      <SelectTrigger className="w-44"><SelectValue placeholder="— Sin especificar —" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none__">— Sin especificar —</SelectItem>
                        {IVA_CONDITIONS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2"><Label>Email</Label><Input type="email" value={ncEmail} onChange={(e) => setNcEmail(e.target.value)} className="w-44" /></div>
                  <div className="grid gap-2"><Label>Teléfono</Label><Input value={ncPhone} onChange={(e) => setNcPhone(e.target.value)} className="w-36" /></div>
                  <Button size="sm" disabled={ncSaving || !ncNombre.trim()} onClick={crearClienteRapido}><UserPlus />{ncSaving ? 'Guardando…' : 'Crear cliente'}</Button>
                  <Button size="sm" type="button" variant="ghost" onClick={() => setNuevoCliente(false)}>Cancelar</Button>
                </div>
              )}

              <div className="grid gap-2">
                <Label>Ítems</Label>
                {items.map((row, i) => (
                  <div key={i} className="relative flex flex-wrap items-center gap-2">
                    <Input
                      value={row.nombre} onChange={(e) => buscarProducto(i, e.target.value)}
                      placeholder="Producto o descripción…" className="w-56"
                    />
                    {sugerencias?.index === i && sugerencias.items.length > 0 && (
                      <div className="absolute top-9 left-0 z-10 w-56 rounded-md border bg-popover shadow-md">
                        {sugerencias.items.map((p) => (
                          <button
                            key={p.id} type="button"
                            className="block w-full px-3 py-1.5 text-left text-sm hover:bg-accent"
                            onClick={() => elegirProducto(i, p)}
                          >
                            {p.nombre} — {formatCurrency(p.precio_venta)}
                          </button>
                        ))}
                      </div>
                    )}
                    <Input type="number" step="0.01" value={row.qty} onChange={(e) => updateItem(i, 'qty', e.target.value)} className="w-20" placeholder="Cant." />
                    <MoneyInput value={row.precio} onChange={(v) => updateItem(i, 'precio', v)} className="w-32" placeholder="Precio" />
                    <span className="w-28 text-sm text-muted-foreground">{formatCurrency((Number(row.qty) || 0) * (Number(row.precio) || 0))}</span>
                    {items.length > 1 && <Button size="sm" variant="ghost" onClick={() => removeItemRow(i)}><X />Quitar</Button>}
                  </div>
                ))}
                <Button size="sm" variant="outline" className="w-fit" onClick={addItemRow}><Plus />Agregar ítem</Button>
              </div>

              <div className="grid gap-2">
                <Label>Pagos</Label>
                {pagos.map((row, i) => (
                  <div key={i} className="flex flex-wrap items-center gap-2">
                    <Select value={row.medio} onValueChange={(v) => updatePago(i, 'medio', v)}>
                      <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {/* 🔴 Del motor. Esta lista era la copia TypeScript, y
                            el backend ahora **valida** el medio: ofrecer uno que
                            no está en la canónica —`cheque`— daba un 422 recién
                            al guardar la venta, con el mostrador esperando. */}
                        {medios.map((m) => <SelectItem key={m.id} value={m.id}>{m.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <MoneyInput value={montoDeFila(row, i)} onChange={(v) => updateMontoPago(i, v)} className="w-32" placeholder="Monto" />
                    <Input value={row.referencia} onChange={(e) => updatePago(i, 'referencia', e.target.value)} className="w-40" placeholder="Referencia" />
                    {/* 🔴 Sólo en el medio del QR, y apagado por defecto: cargar
                        un pago acá significa que la plata YA está, que es el caso
                        de la enorme mayoría de las ventas. Este check es para
                        decir lo contrario. */}
                    {row.medio === MEDIO_DEL_QR && (
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={row.cobrarConQr}
                          onChange={(e) => updatePagoQr(i, e.target.checked)}
                          className="size-4"
                        />
                        Cobrar con QR ahora
                      </label>
                    )}
                    {pagos.length > 1 && <Button size="sm" variant="ghost" onClick={() => removePagoRow(i)}><X />Quitar</Button>}
                  </div>
                ))}
                <Button size="sm" variant="outline" className="w-fit" onClick={addPagoRow}><Plus />Agregar pago</Button>
                {Math.abs(difCalc) > 0.01 && (
                  <p className="text-sm text-amber-700 dark:text-amber-400">
                    {difCalc > 0 ? `Falta cubrir ${formatCurrency(difCalc)}` : `Vuelto: ${formatCurrency(Math.abs(difCalc))}`}
                  </p>
                )}
              </div>

              <div className="flex flex-wrap items-end gap-4 border-t pt-4">
                <div className="grid gap-2"><Label>Descuento</Label><MoneyInput value={descuento} onChange={setDescuento} className="w-32" /></div>
                <p className="text-sm">Subtotal: <span className="font-medium">{formatCurrency(subtotalCalc)}</span></p>
                <p className="text-sm">Total: <span className="font-medium">{formatCurrency(totalCalc)}</span></p>
              </div>
            </div>

            <DialogFooter>
              <DialogClose asChild><Button type="button" variant="outline">Cancelar</Button></DialogClose>
              <Button disabled={savingVenta} onClick={crearVenta}><CheckCircle2 />{savingVenta ? 'Guardando…' : 'Registrar venta'}</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="todas"><ListChecks />Todas</TabsTrigger>
          <TabsTrigger value="sin_facturar"><ReceiptText />Sin facturar</TabsTrigger>
          <TabsTrigger value="facturadas"><FileCheck />Facturadas</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-2 py-3">
          <div className="grid gap-2"><Label>Desde</Label><Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="w-40" /></div>
          <div className="grid gap-2"><Label>Hasta</Label><Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="w-40" /></div>
          <div className="grid gap-2">
            <Label>Buscar</Label>
            <Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()} className="min-w-48" placeholder="Buscar…" />
          </div>
          <Button size="sm" variant="outline" onClick={load}>Filtrar</Button>
          {(q || desde || hasta) && <Button size="sm" variant="outline" onClick={limpiarFiltros}>Limpiar</Button>}
        </CardContent>
      </Card>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={ventas} emptyMessage={emptyMessage} onRowClick={(v) => navigate(`/ventas/${v.id}`)} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
