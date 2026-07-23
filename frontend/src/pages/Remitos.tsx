import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type Cliente, type Remito } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  FileText, Plus, Search, X, Eye, FileDown, Trash2,
} from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

type ItemRow = { description: string; qty: string }
const EMPTY_ITEM: ItemRow = { description: '', qty: '1' }

export function Remitos() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [remitos, setRemitos] = useState<Remito[]>([])
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')

  const [creating, setCreating] = useState(false)
  const [clienteId, setClienteId] = useState('')
  const [clienteNombreLibre, setClienteNombreLibre] = useState('')
  const [observations, setObservations] = useState('')
  const [items, setItems] = useState<ItemRow[]>([{ ...EMPTY_ITEM }])
  const [saving, setSaving] = useState(false)

  const [abiertoId, setAbiertoId] = useState<number | null>(null)
  const [detalle, setDetalle] = useState<Remito | null>(null)

  useEffect(() => {
    api.get<Cliente[]>('/api/clientes').then((c) => setClientes(c.filter((x) => x.activo))).catch(() => {})
  }, [])

  useEffect(() => { load() }, [])

  // Deep-link desde accesos rapidos del Dashboard (?nuevo=1)
  useEffect(() => {
    if (searchParams.get('nuevo') === '1') {
      setCreating(true)
      setSearchParams((p) => { p.delete('nuevo'); return p }, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Deep-link desde otros modulos (ej. Ventas): ?ver=<id> abre el detalle de ese remito
  useEffect(() => {
    const ver = searchParams.get('ver')
    if (ver) verDetalle(Number(ver))
    if (ver) setSearchParams((p) => { p.delete('ver'); return p }, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setRemitos(await api.get<Remito[]>(`/api/remitos${q ? `?q=${encodeURIComponent(q)}` : ''}`))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function limpiarBusqueda() {
    setQ('')
    setTimeout(load, 0)
  }

  async function verDetalle(id: number) {
    if (abiertoId === id) {
      setAbiertoId(null)
      return
    }
    setAbiertoId(id)
    setError(null)
    try {
      setDetalle(await api.get<Remito>(`/api/remitos/${id}`))
    } catch (err) {
      setError(describeError(err))
    }
  }

  function addItem() {
    setItems((rows) => [...rows, { ...EMPTY_ITEM }])
  }
  function removeItem(i: number) {
    setItems((rows) => rows.filter((_, idx) => idx !== i))
  }
  function updateItem(i: number, field: keyof ItemRow, value: string) {
    setItems((rows) => rows.map((r, idx) => idx === i ? { ...r, [field]: value } : r))
  }

  function resetForm() {
    setClienteId(''); setClienteNombreLibre(''); setObservations(''); setItems([{ ...EMPTY_ITEM }])
  }

  async function crear() {
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/remitos', {
        date: todayIso(), client_id: clienteId ? Number(clienteId) : null,
        client_name: clienteId ? '' : clienteNombreLibre, observations,
        items: items.filter((r) => r.description.trim()).map((r) => ({ description: r.description, qty: Number(r.qty) || 0 })),
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

  async function eliminar(r: Remito) {
    if (!window.confirm('¿Eliminar este remito? Esta acción no se puede deshacer.')) return
    setError(null)
    try {
      await api.del(`/api/remitos/${r.id}`)
      if (abiertoId === r.id) setAbiertoId(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const columns = useMemo<ColumnDef<Remito>[]>(() => [
    { accessorKey: 'number', header: sortableHeader('Número'), cell: ({ row }) => <span className="font-mono text-sm">{row.original.number}</span> },
    { accessorKey: 'date', header: 'Fecha' },
    { accessorKey: 'client_name', header: 'Cliente' },
    { accessorKey: 'observations', header: 'Observaciones', cell: ({ row }) => row.original.observations || '—' },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => verDetalle(row.original.id)}>
            <Eye />{abiertoId === row.original.id ? 'Ocultar' : 'Ver'}
          </Button>
          <Button asChild size="sm" variant="outline"><a href={`/remitos/${row.original.id}/pdf`} target="_blank" rel="noreferrer"><FileDown />PDF</a></Button>
          <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}><Trash2 />Eliminar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [abiertoId])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><FileText className="size-5" />Remitos</h2>
        <div className="flex items-end gap-3">
          <div className="grid gap-1.5">
            <Label>Buscar</Label>
            <div className="flex gap-1">
              <Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()} className="w-56" placeholder="Número, cliente u observaciones…" />
              <Button size="icon" variant="outline" onClick={load}><Search /></Button>
              {q && <Button size="icon" variant="outline" onClick={limpiarBusqueda}><X /></Button>}
            </div>
          </div>
          {!creating && <Button onClick={() => setCreating(true)}><Plus />Nuevo remito</Button>}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {creating && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nuevo remito</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex flex-wrap items-end gap-3">
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
                <div className="grid gap-1.5"><Label>o nombre libre</Label><Input value={clienteNombreLibre} onChange={(e) => setClienteNombreLibre(e.target.value)} className="w-48" /></div>
              )}
              <div className="grid gap-1.5 flex-1"><Label>Observaciones</Label><Input value={observations} onChange={(e) => setObservations(e.target.value)} /></div>
            </div>

            <div className="grid gap-2">
              <Label>Ítems</Label>
              {items.map((row, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2">
                  <Input value={row.description} onChange={(e) => updateItem(i, 'description', e.target.value)} className="w-64" placeholder="Descripción" />
                  <Input type="number" step="0.01" value={row.qty} onChange={(e) => updateItem(i, 'qty', e.target.value)} className="w-20" placeholder="Cant." />
                  {items.length > 1 && <Button size="sm" variant="ghost" onClick={() => removeItem(i)}><X />Quitar</Button>}
                </div>
              ))}
              <Button size="sm" variant="outline" className="w-fit" onClick={addItem}><Plus />Agregar ítem</Button>
            </div>

            <div className="flex gap-2">
              <Button disabled={saving} onClick={crear}>{saving ? 'Guardando…' : 'Guardar y generar PDF'}</Button>
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
            <DataTable columns={columns} data={remitos} emptyMessage="Sin remitos todavía." />
          )}
        </CardContent>
      </Card>

      {abiertoId !== null && detalle && (
        <div className="grid gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">Datos del cliente</CardTitle></CardHeader>
              <CardContent className="grid gap-1.5 text-sm">
                <p><span className="text-muted-foreground">Cliente:</span> {detalle.client_name}</p>
                {detalle.client_cuit && <p><span className="text-muted-foreground">CUIT / DNI:</span> {detalle.client_cuit}</p>}
                {detalle.client_address && <p><span className="text-muted-foreground">Domicilio:</span> {detalle.client_address}</p>}
                {detalle.client_email && <p><span className="text-muted-foreground">Email:</span> {detalle.client_email}</p>}
                {detalle.client_phone && <p><span className="text-muted-foreground">Teléfono:</span> {detalle.client_phone}</p>}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Datos del remito</CardTitle></CardHeader>
              <CardContent className="grid gap-1.5 text-sm">
                <p><span className="text-muted-foreground">Número:</span> <span className="font-mono">{detalle.number}</span></p>
                <p><span className="text-muted-foreground">Fecha:</span> {detalle.date}</p>
                {detalle.observations && <p><span className="text-muted-foreground">Observaciones:</span> {detalle.observations}</p>}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle className="text-base">Ítems</CardTitle></CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead className="border-b text-muted-foreground">
                  <tr>
                    <th className="p-3 text-left font-medium">Descripción</th>
                    <th className="p-3 text-right font-medium">Cantidad</th>
                  </tr>
                </thead>
                <tbody>
                  {detalle.items.map((it, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="whitespace-pre-line p-3">{it.description}</td>
                      <td className="p-3 text-right">{it.qty}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <div className="flex justify-end gap-2">
            <Button asChild variant="outline"><a href={`/remitos/${detalle.id}/pdf`} target="_blank" rel="noreferrer"><FileDown />Ver PDF</a></Button>
            <Button variant="outline" onClick={() => eliminar(detalle)}><Trash2 />Eliminar remito</Button>
          </div>
        </div>
      )}
    </div>
  )
}
