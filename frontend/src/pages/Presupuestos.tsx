import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, ESTADOS_PRESUPUESTO, type Cliente, type Presupuesto } from '../api'
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

type ItemRow = { description: string; qty: string; unit_price: string }
const EMPTY_ITEM: ItemRow = { description: '', qty: '1', unit_price: '0' }

const estadoVariant: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  aceptado: 'default', enviado: 'secondary', borrador: 'outline', rechazado: 'destructive', vencido: 'destructive', facturado: 'default',
}

export function Presupuestos() {
  const [presupuestos, setPresupuestos] = useState<Presupuesto[]>([])
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [estadoFiltro, setEstadoFiltro] = useState('')

  const [creating, setCreating] = useState(false)
  const [clienteId, setClienteId] = useState('')
  const [clienteNombreLibre, setClienteNombreLibre] = useState('')
  const [validUntil, setValidUntil] = useState('')
  const [taxRate, setTaxRate] = useState('0.21')
  const [observations, setObservations] = useState('')
  const [items, setItems] = useState<ItemRow[]>([{ ...EMPTY_ITEM }])
  const [saving, setSaving] = useState(false)

  const [abiertoId, setAbiertoId] = useState<number | null>(null)
  const [emailTo, setEmailTo] = useState('')

  useEffect(() => {
    api.get<Cliente[]>('/api/clientes').then((c) => setClientes(c.filter((x) => x.activo))).catch(() => {})
  }, [])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estadoFiltro])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ items: Presupuesto[] }>(`/api/presupuestos?estado=${estadoFiltro}${q ? `&q=${encodeURIComponent(q)}` : ''}`)
      setPresupuestos(data.items)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function addItem() { setItems((rows) => [...rows, { ...EMPTY_ITEM }]) }
  function removeItem(i: number) { setItems((rows) => rows.filter((_, idx) => idx !== i)) }
  function updateItem(i: number, field: keyof ItemRow, value: string) {
    setItems((rows) => rows.map((r, idx) => idx === i ? { ...r, [field]: value } : r))
  }

  function resetForm() {
    setClienteId(''); setClienteNombreLibre(''); setValidUntil(''); setTaxRate('0.21')
    setObservations(''); setItems([{ ...EMPTY_ITEM }])
  }

  async function crear() {
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/presupuestos', {
        date: todayIso(), valid_until: validUntil, client_id: clienteId ? Number(clienteId) : null,
        client_name: clienteId ? '' : clienteNombreLibre, tax_rate: Number(taxRate) || 0, observations,
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

  async function cambiarEstado(p: Presupuesto, estado: string, convertirRemito = false) {
    setError(null)
    try {
      await api.post(`/api/presupuestos/${p.id}/estado`, { estado, convertir_remito: convertirRemito })
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function enviarEmail(p: Presupuesto) {
    if (!emailTo.trim()) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/presupuestos/${p.id}/enviar-email`, { email: emailTo })
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function eliminar(p: Presupuesto) {
    setError(null)
    try {
      await api.del(`/api/presupuestos/${p.id}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const columns = useMemo<ColumnDef<Presupuesto>[]>(() => [
    { accessorKey: 'number', header: sortableHeader('Número'), cell: ({ row }) => <span className="font-mono text-sm">{row.original.number}</span> },
    { accessorKey: 'date', header: 'Fecha' },
    { accessorKey: 'client_name', header: 'Cliente' },
    { accessorKey: 'total', header: 'Total', cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.total)}</span> },
    {
      accessorKey: 'status',
      header: 'Estado',
      cell: ({ row }) => <Badge variant={estadoVariant[row.original.status] ?? 'outline'}>{row.original.status}</Badge>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => { setAbiertoId(abiertoId === row.original.id ? null : row.original.id); setEmailTo('') }}>
            {abiertoId === row.original.id ? 'Ocultar' : 'Gestionar'}
          </Button>
          <Button asChild size="sm" variant="outline"><a href={`/presupuestos/${row.original.id}/pdf`} target="_blank" rel="noreferrer">PDF</a></Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [abiertoId])

  const presupuestoAbierto = presupuestos.find((p) => p.id === abiertoId)

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">Presupuestos</h2>
        <div className="flex items-end gap-3">
          <div className="grid gap-1.5"><Label>Buscar</Label><Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()} className="w-48" /></div>
          <div className="grid gap-1.5">
            <Label>Estado</Label>
            <Select value={estadoFiltro || '__todos__'} onValueChange={(v) => setEstadoFiltro(v === '__todos__' ? '' : v)}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__todos__">Todos</SelectItem>
                {ESTADOS_PRESUPUESTO.map((e) => <SelectItem key={e} value={e}>{e}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {!creating && <Button onClick={() => setCreating(true)}>+ Nuevo presupuesto</Button>}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {creating && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nuevo presupuesto</CardTitle></CardHeader>
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
              <div className="grid gap-1.5"><Label>Válido hasta</Label><Input type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} className="w-40" /></div>
              <div className="grid gap-1.5"><Label>IVA</Label><Input type="number" step="0.01" value={taxRate} onChange={(e) => setTaxRate(e.target.value)} className="w-24" /></div>
            </div>

            <div className="grid gap-2">
              <Label>Ítems</Label>
              {items.map((row, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2">
                  <Input value={row.description} onChange={(e) => updateItem(i, 'description', e.target.value)} className="w-64" placeholder="Descripción" />
                  <Input type="number" step="0.01" value={row.qty} onChange={(e) => updateItem(i, 'qty', e.target.value)} className="w-20" placeholder="Cant." />
                  <Input type="number" step="0.01" value={row.unit_price} onChange={(e) => updateItem(i, 'unit_price', e.target.value)} className="w-28" placeholder="Precio" />
                  {items.length > 1 && <Button size="sm" variant="ghost" onClick={() => removeItem(i)}>Quitar</Button>}
                </div>
              ))}
              <Button size="sm" variant="outline" className="w-fit" onClick={addItem}>+ Agregar ítem</Button>
            </div>

            <div className="grid gap-1.5"><Label>Observaciones</Label><Input value={observations} onChange={(e) => setObservations(e.target.value)} /></div>

            <div className="flex gap-2">
              <Button disabled={saving} onClick={crear}>{saving ? 'Guardando…' : 'Crear presupuesto'}</Button>
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
            <DataTable columns={columns} data={presupuestos} emptyMessage="Sin presupuestos todavía." />
          )}
        </CardContent>
      </Card>

      {presupuestoAbierto && (
        <Card>
          <CardHeader><CardTitle className="text-base">{presupuestoAbierto.number} — {presupuestoAbierto.client_name}</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex flex-wrap gap-2">
              {ESTADOS_PRESUPUESTO.filter((e) => e !== presupuestoAbierto.status).map((e) => (
                <Button key={e} size="sm" variant="outline" onClick={() => cambiarEstado(presupuestoAbierto, e, e === 'aceptado')}>
                  Marcar {e}{e === 'aceptado' ? ' y convertir a remito' : ''}
                </Button>
              ))}
              {presupuestoAbierto.status === 'borrador' && (
                <Button size="sm" variant="outline" onClick={() => eliminar(presupuestoAbierto)}>Eliminar</Button>
              )}
            </div>
            <div className="flex flex-wrap items-end gap-3 border-t pt-4">
              <div className="grid gap-1.5"><Label>Enviar por email</Label><Input type="email" value={emailTo} onChange={(e) => setEmailTo(e.target.value)} className="w-56" /></div>
              <Button size="sm" variant="outline" disabled={saving || !emailTo.trim()} onClick={() => enviarEmail(presupuestoAbierto)}>Enviar</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
