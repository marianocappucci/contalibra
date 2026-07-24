import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, MEDIOS_PAGO_LABELS, type Cliente, type Factura, type FacturaDetalle, type TipoFactura,
} from '../api'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  Eye, FileDown, Printer, ReceiptText, Mail, RefreshCw, FileMinus, FilePlus, Copy, Trash2,
  CheckCircle2, Hourglass, CircleDollarSign, AlertTriangle, Info, CornerDownLeft, ListChecks, Plus,
  Receipt, FileText, Search, X, ChevronLeft, ChevronRight,
} from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

const TIPO_BADGE: Record<number, { label: string; className: string }> = {
  1: { label: 'Fact. A', className: 'bg-primary text-primary-foreground' },
  6: { label: 'Fact. B', className: 'bg-secondary text-secondary-foreground' },
  11: { label: 'Fact. C', className: 'bg-sky-500 text-white' },
  3: { label: 'NC-A', className: 'bg-destructive text-white' },
  8: { label: 'NC-B', className: 'bg-destructive text-white' },
  13: { label: 'NC-C', className: 'bg-destructive text-white' },
  2: { label: 'ND-A', className: 'bg-primary text-primary-foreground' },
  7: { label: 'ND-B', className: 'bg-secondary text-secondary-foreground' },
  12: { label: 'ND-C', className: 'bg-sky-500 text-white' },
}

function labelComprobante(f: Factura): string {
  const letra = ({ 1: 'A', 6: 'B', 11: 'C', 3: 'NC-A', 8: 'NC-B', 13: 'NC-C', 2: 'ND-A', 7: 'ND-B', 12: 'ND-C' } as Record<number, string>)[f.tipo] ?? '?'
  const pv = String(f.punto_venta).padStart(4, '0')
  const num = String(f.numero).padStart(8, '0')
  return `${letra} ${pv}-${num}`
}

function medioLabel(m: string): string {
  return (MEDIOS_PAGO_LABELS as Record<string, string>)[m] ?? m
}

function estaAutorizada(f: Factura): boolean {
  return Boolean(f.cae) && f.cae !== 'PENDIENTE'
}

type ItemRow = { description: string; qty: string; unit_price: string }
const EMPTY_ITEM: ItemRow = { description: '', qty: '1', unit_price: '0' }

const CONDICIONES_VENTA = [
  'Contado', 'Tarjeta de Débito', 'Tarjeta de Crédito', 'Cuenta Corriente',
  'Cheque', 'Transferencia Bancaria', 'Otros medios de pago electrónico', 'Otra',
]

export function Facturas() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [facturas, setFacturas] = useState<Factura[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [vista, setVista] = useState('facturas')
  const [q, setQ] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState<number | null>(null)
  const [totalPages, setTotalPages] = useState(1)
  const [sinCobrarCount, setSinCobrarCount] = useState(0)

  const [tiposInfo, setTiposInfo] = useState<{ tipos: TipoFactura[]; conceptos: TipoFactura[]; punto_venta: number } | null>(null)
  const [clientes, setClientes] = useState<Cliente[]>([])

  const [creating, setCreating] = useState(false)
  const [tipo, setTipo] = useState('')
  const [clienteId, setClienteId] = useState('')
  const [clienteNombreLibre, setClienteNombreLibre] = useState('')
  const [concepto, setConcepto] = useState('1')
  const [condicionVenta, setCondicionVenta] = useState('Contado')
  const [taxRate, setTaxRate] = useState('0.21')
  const [observations, setObservations] = useState('')
  const [items, setItems] = useState<ItemRow[]>([{ ...EMPTY_ITEM }])
  const [saving, setSaving] = useState(false)

  const [abiertaId, setAbiertaId] = useState<number | null>(null)
  const [detalle, setDetalle] = useState<FacturaDetalle | null>(null)
  const [detalleLoading, setDetalleLoading] = useState(false)
  const [emailTo, setEmailTo] = useState('')
  const [cobroPagos, setCobroPagos] = useState<{ medio: string; monto: string; referencia: string }[]>([{ medio: 'efectivo', monto: '', referencia: '' }])

  useEffect(() => {
    api.get<{ tipos: TipoFactura[]; conceptos: TipoFactura[]; punto_venta: number }>('/api/facturas/tipos').then(setTiposInfo).catch(() => {})
    api.get<Cliente[]>('/api/clientes').then((c) => setClientes(c.filter((x) => x.activo))).catch(() => {})
  }, [])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vista, page])

  useEffect(() => {
    // Contador para el badge de la pestaña "Sin cobrar", independiente del filtro/pagina activos.
    api.get<{ total: number }>('/api/facturas?vista=sin_cobrar').then((d) => setSinCobrarCount(d.total)).catch(() => {})
  }, [facturas])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  function buildQuery(): string {
    const params = new URLSearchParams({ vista, page: String(page) })
    if (q) params.set('q', q)
    if (desde) params.set('desde', desde)
    if (hasta) params.set('hasta', hasta)
    return params.toString()
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ items: Factura[]; total: number; total_pages: number }>(`/api/facturas?${buildQuery()}`)
      setFacturas(data.items)
      setTotal(data.total)
      setTotalPages(data.total_pages)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function buscar() {
    setPage(1)
    load()
  }

  function limpiarFiltros() {
    setQ(''); setDesde(''); setHasta(''); setPage(1)
    setTimeout(load, 0)
  }

  function addItemRow() {
    setItems((rows) => [...rows, { ...EMPTY_ITEM }])
  }
  function removeItemRow(i: number) {
    setItems((rows) => rows.filter((_, idx) => idx !== i))
  }
  function updateItem(i: number, field: keyof ItemRow, value: string) {
    setItems((rows) => rows.map((r, idx) => idx === i ? { ...r, [field]: value } : r))
  }

  const subtotalCalc = items.reduce((acc, r) => acc + (Number(r.qty) || 0) * (Number(r.unit_price) || 0), 0)
  const ivaCalc = tipo === '11' ? 0 : subtotalCalc * (Number(taxRate) || 0)

  function resetForm() {
    setItems([{ ...EMPTY_ITEM }]); setClienteId(''); setClienteNombreLibre('')
    setConcepto('1'); setCondicionVenta('Contado'); setObservations('')
  }

  async function crear() {
    if (!tipo) return
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/facturas', {
        tipo: Number(tipo), punto_venta: tiposInfo?.punto_venta ?? 1, concepto: Number(concepto),
        condicion_venta: condicionVenta, fecha: todayIso(), observations, tax_rate: Number(taxRate) || 0,
        client_id: clienteId ? Number(clienteId) : null, client_name: clienteId ? '' : clienteNombreLibre,
        items: items.filter((r) => r.description.trim()).map((r) => ({
          description: r.description, qty: Number(r.qty) || 0, unit_price: Number(r.unit_price) || 0,
        })),
      })
      setCreating(false)
      resetForm()
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function verDetallePorId(id: number) {
    setAbiertaId(id)
    setDetalleLoading(true)
    setError(null)
    try {
      const data = await api.get<FacturaDetalle>(`/api/facturas/${id}`)
      setDetalle(data)
      setEmailTo(data.cliente_email || '')
      setCobroPagos([{ medio: 'efectivo', monto: String(data.pendiente || ''), referencia: '' }])
    } catch (err) {
      setError(describeError(err))
    } finally {
      setDetalleLoading(false)
    }
  }

  async function verDetalle(f: Factura) {
    if (abiertaId === f.id) {
      setAbiertaId(null)
      return
    }
    await verDetallePorId(f.id)
  }

  // Deep-link desde el Dashboard: ?nuevo=1 abre el alta, ?ver=<id> abre el detalle de esa factura
  useEffect(() => {
    const nuevo = searchParams.get('nuevo')
    const ver = searchParams.get('ver')
    if (nuevo === '1') setCreating(true)
    if (ver) verDetallePorId(Number(ver))
    if (nuevo || ver) setSearchParams((p) => { p.delete('nuevo'); p.delete('ver'); return p }, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function refrescarDetalle() {
    if (abiertaId === null) return
    const data = await api.get<FacturaDetalle>(`/api/facturas/${abiertaId}`)
    setDetalle(data)
  }

  async function autorizar() {
    if (abiertaId === null) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/facturas/${abiertaId}/autorizar`)
      await refrescarDetalle()
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function cobrar() {
    if (abiertaId === null) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/facturas/${abiertaId}/cobrar`, {
        fecha: todayIso(),
        pagos: cobroPagos.filter((p) => Number(p.monto) > 0).map((p) => ({ medio_id: p.medio, monto: Number(p.monto), referencia: p.referencia })),
      })
      await refrescarDetalle()
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function enviarEmail() {
    if (abiertaId === null || !emailTo.trim()) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/facturas/${abiertaId}/enviar-email`, { email: emailTo })
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function crearNota(kind: 'nota-credito' | 'nota-debito') {
    if (abiertaId === null || !detalle) return
    const label = kind === 'nota-credito' ? 'Nota de Crédito' : 'Nota de Débito'
    const relacion = kind === 'nota-credito' ? 'anula' : 'está asociada a'
    const confirmado = window.confirm(
      `Estás por generar una ${label} que ${relacion} el comprobante ${labelComprobante(detalle.factura)} `
      + `(${detalle.factura.cliente_razon}) por ${formatCurrency(detalle.factura.total)}.\n\n`
      + 'Esta acción no se puede deshacer y enviará el comprobante a ARCA para su autorización.',
    )
    if (!confirmado) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/facturas/${abiertaId}/${kind}`)
      setAbiertaId(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  function duplicar() {
    if (!detalle) return
    const f = detalle.factura
    const cliente = clientes.find((c) => c.cuit_dni && c.cuit_dni === f.cliente_cuit)
    setTipo(String(f.tipo))
    if (cliente) {
      setClienteId(String(cliente.id))
      setClienteNombreLibre('')
    } else {
      setClienteId('')
      setClienteNombreLibre(f.cliente_razon)
    }
    setConcepto(String(f.concepto || 1))
    setCondicionVenta(f.condicion_venta || 'Contado')
    setTaxRate(f.subtotal > 0 ? String(Math.round((f.iva_amount / f.subtotal) * 10000) / 10000) : '0.21')
    setObservations('')
    setItems(f.items.map((it) => ({ description: it.description, qty: String(it.qty), unit_price: String(it.unit_price) })))
    setAbiertaId(null)
    setCreating(true)
  }

  async function eliminar() {
    if (abiertaId === null || !detalle) return
    if (!window.confirm('¿Eliminar esta factura? Esta acción no se puede deshacer.')) return
    setSaving(true)
    setError(null)
    try {
      await api.del(`/api/facturas/${abiertaId}`)
      setAbiertaId(null)
      setDetalle(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  const columns = useMemo<ColumnDef<Factura>[]>(() => {
    const cols: ColumnDef<Factura>[] = [
      {
        accessorKey: 'numero',
        header: sortableHeader('Número'),
        cell: ({ row }) => <span className="font-mono text-sm">{String(row.original.punto_venta).padStart(4, '0')}-{String(row.original.numero).padStart(8, '0')}</span>,
      },
      {
        id: 'tipo',
        header: 'Tipo',
        cell: ({ row }) => {
          const b = TIPO_BADGE[row.original.tipo] ?? { label: '?', className: 'bg-secondary text-secondary-foreground' }
          return <Badge className={b.className}>{b.label}</Badge>
        },
      },
      { accessorKey: 'fecha', header: 'Fecha' },
      { accessorKey: 'cliente_razon', header: 'Cliente' },
    ]
    if (vista === 'nc' || vista === 'nd') {
      cols.push({
        id: 'cbte_asoc',
        header: 'Cbte. asociado',
        cell: ({ row }) => row.original.cbte_asoc_nro
          ? <span className="font-mono text-xs text-muted-foreground">{String(row.original.cbte_asoc_pv ?? 0).padStart(4, '0')}-{String(row.original.cbte_asoc_nro).padStart(8, '0')}</span>
          : null,
      })
    }
    cols.push(
      {
        accessorKey: 'total',
        header: 'Total',
        cell: ({ row }) => (
          <span className={`font-medium ${vista === 'nc' ? 'text-destructive' : vista === 'nd' ? 'text-primary' : ''}`}>
            {vista === 'nc' ? '- ' : vista === 'nd' ? '+ ' : ''}{formatCurrency(row.original.total)}
          </span>
        ),
      },
      {
        id: 'estado',
        header: 'Estado',
        cell: ({ row }) => {
          const f = row.original
          if (!estaAutorizada(f)) return <Badge variant="secondary">Sin CAE</Badge>
          if (vista === 'nc' || vista === 'nd') return <Badge variant="default"><CheckCircle2 />Autorizada</Badge>
          const tc = f.total_cobrado ?? 0
          if (tc >= f.total) return <Badge variant="default"><CheckCircle2 />Cobrada</Badge>
          if (tc > 0) return <Badge variant="secondary"><Hourglass />Parcial</Badge>
          return <Badge variant="outline"><Hourglass />Sin cobrar</Badge>
        },
      },
      {
        id: 'actions',
        header: () => <div className="text-right">Acciones</div>,
        cell: ({ row }) => {
          const f = row.original
          const tc = f.total_cobrado ?? 0
          const puedeCobrar = (vista === 'facturas' || vista === 'sin_cobrar') && estaAutorizada(f) && tc < f.total
          return (
            <div className="flex justify-end gap-2">
              {puedeCobrar && (
                <Button size="sm" variant="outline" title="Registrar cobro" onClick={() => verDetalle(f)}>
                  <CircleDollarSign />
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={() => verDetalle(f)}>
                <Eye />{abiertaId === f.id ? 'Ocultar' : 'Ver'}
              </Button>
              <Button asChild size="sm" variant="outline"><a href={`/facturas/${f.id}/pdf`} target="_blank" rel="noreferrer"><FileDown />PDF</a></Button>
            </div>
          )
        },
      },
    )
    return cols
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abiertaId, vista])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Receipt className="size-5 text-primary" />Comprobantes</h2>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button><Plus />Nuevo</Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setCreating(true)}>
              <FileText className="text-primary" />Factura
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled className="flex-col items-start gap-0.5">
              <span className="flex items-center gap-2"><FileMinus className="text-amber-500" />Nota de Crédito</span>
              <span className="pl-6 text-xs text-muted-foreground">Generá desde el detalle de una factura</span>
            </DropdownMenuItem>
            <DropdownMenuItem disabled className="flex-col items-start gap-0.5">
              <span className="flex items-center gap-2"><FilePlus className="text-sky-500" />Nota de Débito</span>
              <span className="pl-6 text-xs text-muted-foreground">Generá desde el detalle de una factura</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Tabs value={vista} onValueChange={(v) => { setVista(v); setPage(1) }}>
        <TabsList>
          <TabsTrigger value="facturas"><Receipt />Facturas</TabsTrigger>
          <TabsTrigger value="sin_cobrar">
            <Hourglass />Sin cobrar
            {sinCobrarCount > 0 && <Badge variant="secondary" className="ml-1">{sinCobrarCount}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="nc"><FileMinus />Notas de Crédito</TabsTrigger>
          <TabsTrigger value="nd"><FilePlus />Notas de Débito</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-2 py-3">
          <Input
            value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && buscar()}
            placeholder="Buscar por número, cliente…" className="min-w-48 flex-1"
          />
          <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} title="Desde" className="w-40" />
          <Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} title="Hasta" className="w-40" />
          <Button variant="outline" size="icon" onClick={buscar}><Search /></Button>
          {(q || desde || hasta) && <Button variant="outline" size="icon" onClick={limpiarFiltros}><X /></Button>}
          {total !== null && (
            <span className="ml-auto text-sm text-muted-foreground">{total} resultado{total !== 1 ? 's' : ''}</span>
          )}
        </CardContent>
      </Card>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {creating && tiposInfo && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nueva factura</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="grid gap-1.5">
                <Label>Tipo</Label>
                <Select value={tipo} onValueChange={setTipo}>
                  <SelectTrigger className="w-36"><SelectValue placeholder="Elegir…" /></SelectTrigger>
                  <SelectContent>
                    {tiposInfo.tipos.map((t) => <SelectItem key={t.value} value={String(t.value)}>{t.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label>Cliente</Label>
                <Select value={clienteId} onValueChange={(v) => { setClienteId(v); setClienteNombreLibre('') }}>
                  <SelectTrigger className="w-52"><SelectValue placeholder="Elegir cliente…" /></SelectTrigger>
                  <SelectContent>
                    {clientes.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {!clienteId && (
                <div className="grid gap-1.5"><Label>o nombre libre</Label><Input value={clienteNombreLibre} onChange={(e) => setClienteNombreLibre(e.target.value)} className="w-48" placeholder="Consumidor Final" /></div>
              )}
              <div className="grid gap-1.5">
                <Label>Concepto</Label>
                <Select value={concepto} onValueChange={setConcepto}>
                  <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {tiposInfo.conceptos.map((c) => <SelectItem key={c.value} value={String(c.value)}>{c.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label>Condición de venta</Label>
                <Select value={condicionVenta} onValueChange={setCondicionVenta}>
                  <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CONDICIONES_VENTA.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {tipo !== '11' && (
                <div className="grid gap-1.5"><Label>IVA</Label><Input type="number" step="0.01" value={taxRate} onChange={(e) => setTaxRate(e.target.value)} className="w-24" /></div>
              )}
            </div>

            <div className="grid gap-2">
              <Label>Ítems</Label>
              {items.map((row, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2">
                  <Input value={row.description} onChange={(e) => updateItem(i, 'description', e.target.value)} className="w-64" placeholder="Descripción" />
                  <Input type="number" step="0.01" value={row.qty} onChange={(e) => updateItem(i, 'qty', e.target.value)} className="w-20" placeholder="Cant." />
                  <Input type="number" step="0.01" value={row.unit_price} onChange={(e) => updateItem(i, 'unit_price', e.target.value)} className="w-28" placeholder="Precio unit." />
                  <span className="w-28 text-sm text-muted-foreground">{formatCurrency((Number(row.qty) || 0) * (Number(row.unit_price) || 0))}</span>
                  {items.length > 1 && <Button size="sm" variant="ghost" onClick={() => removeItemRow(i)}>Quitar</Button>}
                </div>
              ))}
              <Button size="sm" variant="outline" className="w-fit" onClick={addItemRow}><Plus />Agregar ítem</Button>
            </div>

            <div className="grid gap-1.5"><Label>Observaciones</Label><Input value={observations} onChange={(e) => setObservations(e.target.value)} /></div>

            <div className="flex flex-wrap items-end gap-4 border-t pt-4">
              <p className="text-sm">Subtotal: <span className="font-medium">{formatCurrency(subtotalCalc)}</span></p>
              <p className="text-sm">IVA: <span className="font-medium">{formatCurrency(ivaCalc)}</span></p>
              <p className="text-sm">Total: <span className="font-medium">{formatCurrency(subtotalCalc + ivaCalc)}</span></p>
              <Button disabled={saving || !tipo} onClick={crear}>{saving ? 'Emitiendo…' : 'Emitir factura'}</Button>
              <Button type="button" variant="outline" onClick={() => { setCreating(false); resetForm() }}>Cancelar</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable
              columns={columns}
              data={facturas}
              emptyMessage={
                q || desde || hasta ? 'No se encontraron comprobantes con ese criterio.'
                  : vista === 'nc' ? 'No hay notas de crédito registradas aún.'
                  : vista === 'nd' ? 'No hay notas de débito registradas aún.'
                  : 'No hay facturas registradas aún.'
              }
            />
          )}
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1">
          <Button size="icon" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft /></Button>
          {Array.from({ length: totalPages }, (_, i) => i + 1)
            .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
            .map((p, idx, arr) => (
              <span key={p} className="flex items-center gap-1">
                {idx > 0 && arr[idx - 1] !== p - 1 && <span className="px-1 text-muted-foreground">…</span>}
                <Button size="icon" variant={p === page ? 'default' : 'outline'} onClick={() => setPage(p)}>{p}</Button>
              </span>
            ))}
          <Button size="icon" variant="outline" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}><ChevronRight /></Button>
        </div>
      )}

      {abiertaId !== null && (
        <Card>
          <CardHeader><CardTitle className="text-base">{detalle ? labelComprobante(detalle.factura) : ''} — {detalle?.factura.cliente_razon}</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            {detalleLoading || !detalle ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
            ) : (
              <>
                {/* Relación con otros comprobantes */}
                {detalle.factura_original && (
                  <p className="flex items-start gap-2 rounded-md border bg-muted/50 p-3 text-sm">
                    <CornerDownLeft className="mt-0.5 size-4 shrink-0" />
                    <span>
                      Este comprobante anula la {labelComprobante(detalle.factura_original)} del {detalle.factura_original.fecha} — {detalle.factura_original.cliente_razon}.{' '}
                      <Button variant="link" className="h-auto p-0" onClick={() => verDetallePorId(detalle.factura_original!.id)}>Ver comprobante original</Button>
                    </span>
                  </p>
                )}
                {detalle.notas_credito.length > 0 && (
                  <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/40">
                    <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" />
                    <div>
                      <p className="font-medium">{detalle.notas_credito.length === 1 ? 'Nota de crédito asociada' : 'Notas de crédito asociadas'}</p>
                      <ul className="mt-1 grid gap-1">
                        {detalle.notas_credito.map((nc) => (
                          <li key={nc.id} className="flex items-center gap-2">
                            <Button variant="link" className="h-auto p-0 font-mono" onClick={() => verDetallePorId(nc.id)}>{labelComprobante(nc)}</Button>
                            <span className="text-muted-foreground">— {nc.fecha}</span>
                            {estaAutorizada(nc) ? <Badge variant="default">Autorizada</Badge> : <Badge variant="outline">Pendiente</Badge>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
                {detalle.notas_debito.length > 0 && (
                  <div className="flex items-start gap-2 rounded-md border border-blue-300 bg-blue-50 p-3 text-sm dark:border-blue-900 dark:bg-blue-950/40">
                    <Info className="mt-0.5 size-4 shrink-0 text-blue-600 dark:text-blue-400" />
                    <div>
                      <p className="font-medium">{detalle.notas_debito.length === 1 ? 'Nota de débito asociada' : 'Notas de débito asociadas'}</p>
                      <ul className="mt-1 grid gap-1">
                        {detalle.notas_debito.map((nd) => (
                          <li key={nd.id} className="flex items-center gap-2">
                            <Button variant="link" className="h-auto p-0 font-mono" onClick={() => verDetallePorId(nd.id)}>{labelComprobante(nd)}</Button>
                            <span className="text-muted-foreground">— {nd.fecha}</span>
                            {estaAutorizada(nd) ? <Badge variant="default">Autorizada</Badge> : <Badge variant="outline">Pendiente</Badge>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

                {/* Estado de cobro */}
                {[1, 6, 11].includes(detalle.factura.tipo) && (
                  detalle.cobros.length > 0 ? (
                    <div className={`flex flex-wrap items-center gap-2 rounded-md border p-3 text-sm ${detalle.pendiente <= 0 ? 'border-emerald-300 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/40' : 'border-amber-300 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/40'}`}>
                      {detalle.pendiente <= 0 ? <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" /> : <CircleDollarSign className="size-4 shrink-0 text-amber-600 dark:text-amber-400" />}
                      {detalle.pendiente <= 0 ? (
                        <span><strong>Cobrado completo</strong> — {formatCurrency(detalle.total_cobrado)}{detalle.cobros.length > 1 && <span className="text-muted-foreground"> ({detalle.cobros.length} pagos)</span>}</span>
                      ) : (
                        <span><strong>Pago parcial</strong> — Cobrado: {formatCurrency(detalle.total_cobrado)} <span className="font-medium text-destructive">Pendiente: {formatCurrency(detalle.pendiente)}</span></span>
                      )}
                    </div>
                  ) : estaAutorizada(detalle.factura) ? (
                    <div className="flex flex-wrap items-center gap-2 rounded-md border p-3 text-sm">
                      <Hourglass className="size-4 shrink-0 text-muted-foreground" />
                      <span><strong>Pendiente de cobro</strong> — {formatCurrency(detalle.factura.total)}</span>
                    </div>
                  ) : null
                )}

                {detalle.cobros.length > 0 && (
                  <Card className="border-l-4 border-l-emerald-600">
                    <CardHeader className="py-2"><CardTitle className="flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-400"><ListChecks className="size-4" />Cobros registrados</CardTitle></CardHeader>
                    <CardContent className="grid gap-1 py-2 text-sm">
                      {detalle.cobros.map((c) => (
                        <div key={c.id} className="flex flex-wrap items-center justify-between gap-2 border-b py-1 last:border-0">
                          <span className="text-muted-foreground">
                            {c.fecha}
                            {c.medio_pago && <Badge variant="outline" className="ml-2">{medioLabel(c.medio_pago)}</Badge>}
                            {c.referencia && <span className="ml-1">({c.referencia})</span>}
                          </span>
                          <span className="font-medium text-emerald-700 dark:text-emerald-400">+ {formatCurrency(c.monto)}</span>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                )}

                {/* CAE */}
                {estaAutorizada(detalle.factura) ? (
                  <div className="flex items-center gap-2 rounded-md border border-emerald-300 bg-emerald-50 p-3 text-sm dark:border-emerald-900 dark:bg-emerald-950/40">
                    <CheckCircle2 className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                    <span><strong>Comprobante autorizado por ARCA</strong> — CAE: <span className="font-mono">{detalle.factura.cae}</span> · Vence: <strong>{detalle.factura.cae_vto}</strong></span>
                  </div>
                ) : (
                  <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/40">
                    <span className="flex items-center gap-2"><AlertTriangle className="size-4 shrink-0 text-amber-600 dark:text-amber-400" />Comprobante <strong>pendiente de autorización ARCA</strong>.</span>
                    <Button size="sm" variant="outline" disabled={saving} onClick={autorizar}><RefreshCw />Reintentar autorización ARCA</Button>
                  </div>
                )}

                {/* Datos del receptor / comprobante */}
                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <CardHeader><CardTitle className="text-base">Datos del receptor</CardTitle></CardHeader>
                    <CardContent className="grid gap-1.5 text-sm">
                      <p><span className="text-muted-foreground">Razón social:</span> {detalle.factura.cliente_razon}</p>
                      {detalle.factura.cliente_cuit && <p><span className="text-muted-foreground">CUIT:</span> <span className="font-mono">{detalle.factura.cliente_cuit}</span></p>}
                      {detalle.factura.cliente_domicilio && <p><span className="text-muted-foreground">Domicilio:</span> {detalle.factura.cliente_domicilio}</p>}
                      {detalle.iva_label && <p><span className="text-muted-foreground">Cond. IVA:</span> {detalle.iva_label}</p>}
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader><CardTitle className="text-base">Datos del comprobante</CardTitle></CardHeader>
                    <CardContent className="grid gap-1.5 text-sm">
                      <p><span className="text-muted-foreground">Tipo:</span> {detalle.tipo_label}</p>
                      <p><span className="text-muted-foreground">Número:</span> <span className="font-mono">{String(detalle.factura.punto_venta).padStart(4, '0')}-{String(detalle.factura.numero).padStart(8, '0')}</span></p>
                      <p><span className="text-muted-foreground">Fecha:</span> {detalle.factura.fecha}</p>
                      <p><span className="text-muted-foreground">Concepto:</span> {detalle.concepto_label}</p>
                      <p><span className="text-muted-foreground">Cond. de venta:</span> {detalle.factura.condicion_venta || 'Contado'}</p>
                      {detalle.factura_original && (
                        <p>
                          <span className="text-muted-foreground">Cbte. anulado:</span>{' '}
                          <Button variant="link" className="h-auto p-0 font-mono" onClick={() => verDetallePorId(detalle.factura_original!.id)}>{labelComprobante(detalle.factura_original)}</Button>
                        </p>
                      )}
                      {detalle.factura.observaciones && <p><span className="text-muted-foreground">Observaciones:</span> {detalle.factura.observaciones}</p>}
                    </CardContent>
                  </Card>
                </div>

                {/* Ítems */}
                <Card>
                  <CardHeader><CardTitle className="text-base">Ítems</CardTitle></CardHeader>
                  <CardContent className="p-0">
                    <table className="w-full text-sm">
                      <thead className="border-b text-muted-foreground">
                        <tr>
                          <th className="p-3 text-left font-medium">Descripción</th>
                          <th className="p-3 text-right font-medium">Cantidad</th>
                          <th className="p-3 text-right font-medium">Precio unit.</th>
                          <th className="p-3 text-right font-medium">Subtotal</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detalle.factura.items.map((it, i) => (
                          <tr key={i} className="border-b last:border-0">
                            <td className="whitespace-pre-line p-3">{it.description}</td>
                            <td className="p-3 text-right">{it.qty}</td>
                            <td className="p-3 text-right">{formatCurrency(it.unit_price)}</td>
                            <td className="p-3 text-right">{formatCurrency(it.subtotal)}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="font-medium">
                        {detalle.factura.tipo !== 11 && detalle.factura.iva_amount > 0 && (
                          <>
                            <tr><td colSpan={3} className="p-3 text-right text-muted-foreground">Subtotal</td><td className="p-3 text-right">{formatCurrency(detalle.factura.subtotal)}</td></tr>
                            <tr><td colSpan={3} className="p-3 text-right text-muted-foreground">IVA {detalle.factura.subtotal > 0 ? Math.round((detalle.factura.iva_amount / detalle.factura.subtotal) * 100) : 21}%</td><td className="p-3 text-right">{formatCurrency(detalle.factura.iva_amount)}</td></tr>
                          </>
                        )}
                        <tr className="text-base"><td colSpan={3} className="p-3 text-right font-semibold">TOTAL</td><td className="p-3 text-right font-semibold text-primary">{formatCurrency(detalle.factura.total)}</td></tr>
                      </tfoot>
                    </table>
                  </CardContent>
                </Card>

                {/* Acciones */}
                <div className="flex flex-wrap gap-2">
                  <Button asChild size="sm" variant="outline"><a href={`/facturas/${abiertaId}/pdf`} target="_blank" rel="noreferrer"><FileDown />Ver PDF</a></Button>
                  <Button asChild size="sm" variant="outline"><a href={`/facturas/${abiertaId}/ticket`} target="_blank" rel="noreferrer"><Printer />Ticket</a></Button>
                  {detalle.cobros.length > 0 && <Button asChild size="sm" variant="outline"><a href={`/facturas/${abiertaId}/recibo`} target="_blank" rel="noreferrer"><ReceiptText />Recibo</a></Button>}
                  {user?.role === 'admin' && [1, 6, 11].includes(detalle.factura.tipo) && (
                    <>
                      <Button size="sm" variant="outline" disabled={saving} onClick={() => crearNota('nota-debito')}><FilePlus />Nota de débito</Button>
                      <Button size="sm" variant="outline" disabled={saving} onClick={() => crearNota('nota-credito')}><FileMinus />Nota de crédito</Button>
                    </>
                  )}
                  <Button size="sm" variant="outline" onClick={duplicar}><Copy />Duplicar</Button>
                  {user?.role === 'admin' && !estaAutorizada(detalle.factura) && (
                    <Button size="sm" variant="outline" className="text-destructive hover:text-destructive" disabled={saving} onClick={eliminar}><Trash2 />Eliminar</Button>
                  )}
                </div>

                {detalle.pendiente > 0 && [1, 6, 11].includes(detalle.factura.tipo) && (
                  <div className="grid gap-2 border-t pt-4">
                    <Label>Registrar cobro</Label>
                    {cobroPagos.map((p, i) => (
                      <div key={i} className="flex flex-wrap items-center gap-2">
                        <Select value={p.medio} onValueChange={(v) => setCobroPagos((rows) => rows.map((r, idx) => idx === i ? { ...r, medio: v } : r))}>
                          <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {Object.entries(MEDIOS_PAGO_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <Input type="number" step="0.01" value={p.monto} onChange={(e) => setCobroPagos((rows) => rows.map((r, idx) => idx === i ? { ...r, monto: e.target.value } : r))} className="w-28" />
                        <Input value={p.referencia} onChange={(e) => setCobroPagos((rows) => rows.map((r, idx) => idx === i ? { ...r, referencia: e.target.value } : r))} className="w-40" placeholder="Referencia" />
                      </div>
                    ))}
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" className="w-fit" onClick={() => setCobroPagos((rows) => [...rows, { medio: 'efectivo', monto: '', referencia: '' }])}><Plus />Agregar medio</Button>
                      <Button size="sm" disabled={saving} onClick={cobrar}><CircleDollarSign />{saving ? 'Guardando…' : 'Registrar cobro'}</Button>
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap items-end gap-3 border-t pt-4">
                  <div className="grid gap-1.5"><Label>Enviar por email</Label><Input type="email" value={emailTo} onChange={(e) => setEmailTo(e.target.value)} className="w-56" /></div>
                  <Button size="sm" variant="outline" disabled={saving || !emailTo.trim()} onClick={enviarEmail}><Mail />Enviar</Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
