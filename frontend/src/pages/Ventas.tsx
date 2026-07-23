import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, MEDIOS_PAGO_LABELS, type Cliente, type ProductoBusqueda, type Venta,
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
import { DataTable, sortableHeader } from '@/components/data-table'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

type ItemRow = { nombre: string; qty: string; precio: string; producto_id: number | null }
type PagoRow = { medio: string; monto: string; referencia: string }

const EMPTY_ITEM: ItemRow = { nombre: '', qty: '1', precio: '0', producto_id: null }
const EMPTY_PAGO: PagoRow = { medio: 'efectivo', monto: '', referencia: '' }

const estadoVariant: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  cobrada: 'default', parcial: 'secondary', pendiente: 'outline', anulada: 'destructive',
}

export function Ventas() {
  const { user } = useAuth()
  const [ventas, setVentas] = useState<Venta[]>([])
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState('todas')
  const [q, setQ] = useState('')

  const [creating, setCreating] = useState(false)
  const [items, setItems] = useState<ItemRow[]>([{ ...EMPTY_ITEM }])
  const [pagos, setPagos] = useState<PagoRow[]>([{ ...EMPTY_PAGO }])
  const [clienteId, setClienteId] = useState('')
  const [descuento, setDescuento] = useState('0')
  const [observaciones, setObservaciones] = useState('')
  const [saving, setSaving] = useState(false)
  const [sugerencias, setSugerencias] = useState<{ index: number; items: ProductoBusqueda[] } | null>(null)

  useEffect(() => {
    api.get<Cliente[]>('/api/clientes').then((c) => setClientes(c.filter((x) => x.activo))).catch(() => {})
  }, [])

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
      setVentas(await api.get<Venta[]>(`/api/ventas?tab=${tab}${q ? `&q=${encodeURIComponent(q)}` : ''}`))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function buscarProducto(index: number, texto: string) {
    updateItem(index, 'nombre', texto)
    if (texto.trim().length < 2) {
      setSugerencias(null)
      return
    }
    try {
      const res = await api.get<ProductoBusqueda[]>(`/productos/buscar?q=${encodeURIComponent(texto)}`)
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

  function updatePago(index: number, field: keyof PagoRow, value: string) {
    setPagos((rows) => rows.map((r, i) => i === index ? { ...r, [field]: value } : r))
  }

  function addPagoRow() {
    setPagos((rows) => [...rows, { ...EMPTY_PAGO }])
  }

  function removePagoRow(index: number) {
    setPagos((rows) => rows.filter((_, i) => i !== index))
  }

  const subtotalCalc = items.reduce((acc, r) => acc + (Number(r.qty) || 0) * (Number(r.precio) || 0), 0)
  const totalCalc = Math.max(0, subtotalCalc - (Number(descuento) || 0))

  function resetForm() {
    setItems([{ ...EMPTY_ITEM }])
    setPagos([{ ...EMPTY_PAGO }])
    setClienteId(''); setDescuento('0'); setObservaciones('')
  }

  async function crear() {
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/ventas', {
        fecha: todayIso(),
        items: items.filter((r) => r.nombre.trim() && Number(r.qty) > 0).map((r) => ({
          nombre: r.nombre, qty: Number(r.qty), precio: Number(r.precio) || 0, producto_id: r.producto_id,
        })),
        descuento: Number(descuento) || 0,
        cliente_id: clienteId ? Number(clienteId) : null,
        observaciones,
        pagos: pagos.filter((p) => Number(p.monto) > 0).map((p) => ({ medio: p.medio, monto: Number(p.monto), referencia: p.referencia })),
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

  async function anular(venta: Venta) {
    setError(null)
    try {
      await api.post(`/api/ventas/${venta.id}/anular`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const columns = useMemo<ColumnDef<Venta>[]>(() => [
    { accessorKey: 'numero', header: sortableHeader('Número'), cell: ({ row }) => <span className="font-mono text-sm">{row.original.numero}</span> },
    { accessorKey: 'fecha', header: 'Fecha' },
    { accessorKey: 'cliente_nombre', header: 'Cliente', cell: ({ row }) => row.original.cliente_nombre || 'Consumidor Final' },
    { accessorKey: 'total', header: 'Total', cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.total)}</span> },
    { accessorKey: 'factura_display', header: 'Factura', cell: ({ row }) => row.original.factura_display || '—' },
    {
      accessorKey: 'estado',
      header: 'Estado',
      cell: ({ row }) => <Badge variant={estadoVariant[row.original.estado] ?? 'outline'}>{row.original.estado}</Badge>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button asChild size="sm" variant="outline"><a href={`/ventas/${row.original.id}/ticket`} target="_blank" rel="noreferrer">Ticket</a></Button>
          <Button asChild size="sm" variant="outline"><a href={`/ventas/${row.original.id}/recibo`} target="_blank" rel="noreferrer">Recibo</a></Button>
          {user?.role === 'admin' && row.original.estado !== 'anulada' && (
            <Button size="sm" variant="outline" onClick={() => anular(row.original)}>Anular</Button>
          )}
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [user])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">Ventas</h2>
        <div className="flex items-end gap-3">
          <div className="grid gap-1.5">
            <Label>Buscar</Label>
            <Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()} className="w-48" placeholder="Número o cliente…" />
          </div>
          <div className="grid gap-1.5">
            <Label>Vista</Label>
            <Select value={tab} onValueChange={setTab}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="todas">Todas</SelectItem>
                <SelectItem value="sin_facturar">Sin facturar</SelectItem>
                <SelectItem value="facturadas">Facturadas</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {!creating && <Button onClick={() => setCreating(true)}>+ Nueva venta</Button>}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {creating && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nueva venta</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="grid gap-1.5">
                <Label>Cliente</Label>
                <Select value={clienteId} onValueChange={setClienteId}>
                  <SelectTrigger className="w-52"><SelectValue placeholder="Consumidor Final" /></SelectTrigger>
                  <SelectContent>
                    {clientes.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5"><Label>Observaciones</Label><Input value={observaciones} onChange={(e) => setObservaciones(e.target.value)} className="w-64" /></div>
            </div>

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
                  <Input type="number" step="0.01" value={row.precio} onChange={(e) => updateItem(i, 'precio', e.target.value)} className="w-28" placeholder="Precio" />
                  <span className="w-28 text-sm text-muted-foreground">{formatCurrency((Number(row.qty) || 0) * (Number(row.precio) || 0))}</span>
                  {items.length > 1 && <Button size="sm" variant="ghost" onClick={() => removeItemRow(i)}>Quitar</Button>}
                </div>
              ))}
              <Button size="sm" variant="outline" className="w-fit" onClick={addItemRow}>+ Agregar ítem</Button>
            </div>

            <div className="grid gap-2">
              <Label>Pagos</Label>
              {pagos.map((row, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2">
                  <Select value={row.medio} onValueChange={(v) => updatePago(i, 'medio', v)}>
                    <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(MEDIOS_PAGO_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Input type="number" step="0.01" value={row.monto} onChange={(e) => updatePago(i, 'monto', e.target.value)} className="w-28" placeholder="Monto" />
                  <Input value={row.referencia} onChange={(e) => updatePago(i, 'referencia', e.target.value)} className="w-40" placeholder="Referencia" />
                  {pagos.length > 1 && <Button size="sm" variant="ghost" onClick={() => removePagoRow(i)}>Quitar</Button>}
                </div>
              ))}
              <Button size="sm" variant="outline" className="w-fit" onClick={addPagoRow}>+ Agregar pago</Button>
            </div>

            <div className="flex flex-wrap items-end gap-4 border-t pt-4">
              <div className="grid gap-1.5"><Label>Descuento</Label><Input type="number" step="0.01" value={descuento} onChange={(e) => setDescuento(e.target.value)} className="w-28" /></div>
              <p className="text-sm">Subtotal: <span className="font-medium">{formatCurrency(subtotalCalc)}</span></p>
              <p className="text-sm">Total: <span className="font-medium">{formatCurrency(totalCalc)}</span></p>
              <Button disabled={saving} onClick={crear}>{saving ? 'Guardando…' : 'Registrar venta'}</Button>
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
            <DataTable columns={columns} data={ventas} emptyMessage="Sin ventas todavía." />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
