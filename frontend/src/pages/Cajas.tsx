import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, MEDIOS_PAGO_LABELS, type CajaConfig } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { DataTable, sortableHeader } from '@/components/data-table'
import { SquareStack, Plus, Eye, Pencil, Trash2, Star, Check } from 'lucide-react'

const TODOS_MEDIOS = Object.keys(MEDIOS_PAGO_LABELS)

const EMPTY = { nombre: '', descripcion: '', medios_pago: [] as string[] }

export function Cajas() {
  const [cajas, setCajas] = useState<CajaConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)

  useEffect(() => { load() }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setCajas(await api.get<CajaConfig[]>('/api/cajas'))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function startCreate() {
    setEditingId('new')
    setForm(EMPTY)
  }

  function startEdit(c: CajaConfig) {
    setEditingId(c.id)
    setForm({ nombre: c.nombre, descripcion: c.descripcion ?? '', medios_pago: c.medios_pago })
  }

  function toggleMedio(medio: string) {
    setForm((f) => ({
      ...f,
      medios_pago: f.medios_pago.includes(medio) ? f.medios_pago.filter((m) => m !== medio) : [...f.medios_pago, medio],
    }))
  }

  async function guardar() {
    if (!form.nombre.trim()) return
    setSaving(true)
    setError(null)
    try {
      if (editingId === 'new') {
        await api.post('/api/cajas', form)
      } else if (editingId) {
        const original = cajas.find((c) => c.id === editingId)
        await api.put(`/api/cajas/${editingId}`, { ...form, activo: !!original?.activo })
      }
      setEditingId(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function setDefault(c: CajaConfig) {
    setError(null)
    try {
      await api.post(`/api/cajas/${c.id}/set-default`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function eliminar(c: CajaConfig) {
    if (!window.confirm(`¿Eliminar la caja «${c.nombre}»?`)) return
    setError(null)
    try {
      await api.del(`/api/cajas/${c.id}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const columns = useMemo<ColumnDef<CajaConfig>[]>(() => [
    { accessorKey: 'nombre', header: sortableHeader('Nombre'), cell: ({ row }) => (
      <span className="font-medium">
        {row.original.nombre}
        {row.original.es_default ? <Badge variant="secondary" className="ml-2">Por defecto</Badge> : null}
      </span>
    ) },
    { accessorKey: 'descripcion', header: 'Descripción', cell: ({ row }) => row.original.descripcion || '—' },
    { accessorKey: 'medios_pago', header: 'Medios habilitados', cell: ({ row }) => row.original.medios_pago.map((m) => MEDIOS_PAGO_LABELS[m] ?? m).join(', ') || '—' },
    {
      accessorKey: 'activo',
      header: 'Estado',
      cell: ({ row }) => <Badge variant={row.original.activo ? 'default' : 'outline'}>{row.original.activo ? 'Activa' : 'Inactiva'}</Badge>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex flex-wrap justify-end gap-2">
          <Button size="sm" variant="outline" asChild><Link to={`/caja?caja_id=${row.original.id}`}><Eye />Ver movimientos</Link></Button>
          <Button size="sm" variant="outline" onClick={() => startEdit(row.original)}><Pencil />Editar</Button>
          {!row.original.es_default && <Button size="sm" variant="outline" onClick={() => setDefault(row.original)} title="Usar como caja por defecto"><Star />Predeterminar</Button>}
          {!row.original.es_default && <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}><Trash2 /></Button>}
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><SquareStack className="size-5 text-primary" />Cajas</h2>
        {editingId === null && <Button onClick={startCreate}><Plus />Nueva caja</Button>}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {editingId !== null && (
        <Card>
          <CardHeader><CardTitle className="text-base">{editingId === 'new' ? 'Nueva caja' : 'Editar caja'}</CardTitle></CardHeader>
          <CardContent className="grid gap-3">
            <div className="flex flex-wrap items-end gap-3">
              <div className="grid gap-1.5"><Label>Nombre</Label><Input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} className="w-48" placeholder="Ej: Caja mostrador, Caja online…" /></div>
              <div className="grid gap-1.5"><Label>Descripción</Label><Input value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} className="w-64" /></div>
            </div>
            <div className="grid gap-1.5">
              <Label>Medios de pago habilitados</Label>
              <div className="flex flex-wrap gap-3">
                {TODOS_MEDIOS.map((m) => (
                  <label key={m} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={form.medios_pago.includes(m)} onChange={() => toggleMedio(m)} />
                    {MEDIOS_PAGO_LABELS[m]}
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <Button disabled={saving} onClick={guardar}><Check />{saving ? 'Guardando…' : editingId === 'new' ? 'Crear' : 'Guardar'}</Button>
              <Button type="button" variant="outline" onClick={() => setEditingId(null)}>Cancelar</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={cajas} emptyMessage="Sin cajas todavía." />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
