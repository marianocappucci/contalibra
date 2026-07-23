import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type Deposito, type Producto, type StockPorDeposito } from '../api'
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

export function Depositos() {
  const [depositos, setDepositos] = useState<Deposito[]>([])
  const [productos, setProductos] = useState<Producto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [nombre, setNombre] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [saving, setSaving] = useState(false)

  const [productoId, setProductoId] = useState('')
  const [origenId, setOrigenId] = useState('')
  const [destinoId, setDestinoId] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [stockOrigen, setStockOrigen] = useState<StockPorDeposito[]>([])
  const [transfiriendo, setTransfiriendo] = useState(false)

  useEffect(() => {
    load()
    api.get<Producto[]>('/api/productos').then((p) => setProductos(p.filter((x) => x.activo))).catch(() => {})
  }, [])

  useEffect(() => {
    if (productoId) {
      api.get<StockPorDeposito[]>(`/api/depositos/stock-producto/${productoId}`).then(setStockOrigen).catch(() => setStockOrigen([]))
    } else {
      setStockOrigen([])
    }
  }, [productoId])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setDepositos(await api.get<Deposito[]>('/api/depositos'))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function startCreate() {
    setEditingId('new')
    setNombre('')
    setDescripcion('')
  }

  function startEdit(d: Deposito) {
    setEditingId(d.id)
    setNombre(d.nombre)
    setDescripcion(d.descripcion ?? '')
  }

  async function guardar() {
    if (!nombre.trim()) return
    setSaving(true)
    setError(null)
    try {
      if (editingId === 'new') {
        await api.post('/api/depositos', { nombre, descripcion })
      } else if (editingId) {
        const original = depositos.find((d) => d.id === editingId)
        await api.put(`/api/depositos/${editingId}`, { nombre, descripcion, activo: !!original?.activo })
      }
      setEditingId(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function setDefault(d: Deposito) {
    setError(null)
    try {
      await api.post(`/api/depositos/${d.id}/set-default`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function eliminar(d: Deposito) {
    setError(null)
    try {
      await api.del(`/api/depositos/${d.id}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function transferir() {
    setTransfiriendo(true)
    setError(null)
    try {
      await api.post('/api/depositos/transferir', {
        producto_id: Number(productoId), origen_id: Number(origenId), destino_id: Number(destinoId),
        cantidad: Number(cantidad), fecha: todayIso(),
      })
      setCantidad('')
      await load()
      if (productoId) api.get<StockPorDeposito[]>(`/api/depositos/stock-producto/${productoId}`).then(setStockOrigen)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setTransfiriendo(false)
    }
  }

  const columns = useMemo<ColumnDef<Deposito>[]>(() => [
    { accessorKey: 'nombre', header: sortableHeader('Nombre'), cell: ({ row }) => (
      <span className="font-medium">
        {row.original.nombre}
        {row.original.es_default ? <Badge variant="secondary" className="ml-2">Por defecto</Badge> : null}
      </span>
    ) },
    { accessorKey: 'descripcion', header: 'Descripción', cell: ({ row }) => row.original.descripcion || '—' },
    { accessorKey: 'total_productos', header: 'Productos con stock' },
    {
      accessorKey: 'activo',
      header: 'Estado',
      cell: ({ row }) => <Badge variant={row.original.activo ? 'default' : 'outline'}>{row.original.activo ? 'Activo' : 'Inactivo'}</Badge>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          {!row.original.es_default && <Button size="sm" variant="outline" onClick={() => setDefault(row.original)}>Por defecto</Button>}
          <Button size="sm" variant="outline" onClick={() => startEdit(row.original)}>Editar</Button>
          <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}>Eliminar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Depósitos</h2>
        {editingId === null && <Button onClick={startCreate}>+ Nuevo depósito</Button>}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {editingId !== null && (
        <Card>
          <CardHeader><CardTitle className="text-base">{editingId === 'new' ? 'Nuevo depósito' : 'Editar depósito'}</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5"><Label>Nombre</Label><Input value={nombre} onChange={(e) => setNombre(e.target.value)} className="w-48" /></div>
            <div className="grid gap-1.5"><Label>Descripción</Label><Input value={descripcion} onChange={(e) => setDescripcion(e.target.value)} className="w-64" /></div>
            <Button disabled={saving} onClick={guardar}>{saving ? 'Guardando…' : editingId === 'new' ? 'Crear' : 'Guardar'}</Button>
            <Button type="button" variant="outline" onClick={() => setEditingId(null)}>Cancelar</Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={depositos} emptyMessage="Sin depósitos todavía." />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Transferir stock entre depósitos</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5">
              <Label>Producto</Label>
              <Select value={productoId} onValueChange={setProductoId}>
                <SelectTrigger className="w-52"><SelectValue placeholder="Elegir producto…" /></SelectTrigger>
                <SelectContent>
                  {productos.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label>Origen</Label>
              <Select value={origenId} onValueChange={setOrigenId}>
                <SelectTrigger className="w-40"><SelectValue placeholder="Depósito…" /></SelectTrigger>
                <SelectContent>
                  {depositos.map((d) => <SelectItem key={d.id} value={String(d.id)}>{d.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label>Destino</Label>
              <Select value={destinoId} onValueChange={setDestinoId}>
                <SelectTrigger className="w-40"><SelectValue placeholder="Depósito…" /></SelectTrigger>
                <SelectContent>
                  {depositos.map((d) => <SelectItem key={d.id} value={String(d.id)}>{d.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5"><Label>Cantidad</Label><Input type="number" step="0.01" value={cantidad} onChange={(e) => setCantidad(e.target.value)} className="w-28" /></div>
            <Button disabled={transfiriendo || !productoId || !origenId || !destinoId || !cantidad} onClick={transferir}>
              {transfiriendo ? 'Transfiriendo…' : 'Transferir'}
            </Button>
          </div>
          {stockOrigen.length > 0 && (
            <ul className="flex flex-wrap gap-3 text-sm text-muted-foreground">
              {stockOrigen.map((s) => <li key={s.id}>{s.nombre}: <span className="font-medium text-foreground">{s.stock_actual}</span></li>)}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
