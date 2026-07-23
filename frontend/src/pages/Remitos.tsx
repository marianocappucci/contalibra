import { useEffect, useMemo, useState } from 'react'
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

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

type ItemRow = { description: string; qty: string }
const EMPTY_ITEM: ItemRow = { description: '', qty: '1' }

export function Remitos() {
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

  useEffect(() => {
    api.get<Cliente[]>('/api/clientes').then((c) => setClientes(c.filter((x) => x.activo))).catch(() => {})
  }, [])

  useEffect(() => { load() }, [])

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
    setError(null)
    try {
      await api.del(`/api/remitos/${r.id}`)
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
          <Button asChild size="sm" variant="outline"><a href={`/remitos/${row.original.id}/pdf`} target="_blank" rel="noreferrer">PDF</a></Button>
          <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}>Eliminar</Button>
        </div>
      ),
    },
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">Remitos</h2>
        <div className="flex items-end gap-3">
          <div className="grid gap-1.5"><Label>Buscar</Label><Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()} className="w-48" /></div>
          {!creating && <Button onClick={() => setCreating(true)}>+ Nuevo remito</Button>}
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
                  {items.length > 1 && <Button size="sm" variant="ghost" onClick={() => removeItem(i)}>Quitar</Button>}
                </div>
              ))}
              <Button size="sm" variant="outline" className="w-fit" onClick={addItem}>+ Agregar ítem</Button>
            </div>

            <div className="flex gap-2">
              <Button disabled={saving} onClick={crear}>{saving ? 'Guardando…' : 'Crear remito'}</Button>
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
    </div>
  )
}
