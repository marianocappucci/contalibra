import { useEffect, useState } from 'react'
import { api, ApiError, type Deposito, type Producto, type StockItem, type StockPorDeposito } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  ArrowLeftRight, Building2, Check, Eye, Info, Package, Pencil, Plus, Star, Trash2,
} from 'lucide-react'

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
  const [activoEdit, setActivoEdit] = useState(true)
  const [saving, setSaving] = useState(false)

  const [productoId, setProductoId] = useState('')
  const [origenId, setOrigenId] = useState('')
  const [destinoId, setDestinoId] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [fechaTransf, setFechaTransf] = useState(todayIso())
  const [observaciones, setObservaciones] = useState('')
  const [stockOrigen, setStockOrigen] = useState<StockPorDeposito[]>([])
  const [transfiriendo, setTransfiriendo] = useState(false)

  const [verStockId, setVerStockId] = useState<number | null>(null)
  const [stockDeposito, setStockDeposito] = useState<StockItem[]>([])
  const [stockLoading, setStockLoading] = useState(false)

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

  useEffect(() => {
    if (verStockId === null) { setStockDeposito([]); return }
    setStockLoading(true)
    api.get<StockItem[]>(`/api/depositos/${verStockId}/stock`)
      .then(setStockDeposito)
      .catch(() => setStockDeposito([]))
      .finally(() => setStockLoading(false))
  }, [verStockId])

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
    setActivoEdit(true)
  }

  function startEdit(d: Deposito) {
    setEditingId(d.id)
    setNombre(d.nombre)
    setDescripcion(d.descripcion ?? '')
    setActivoEdit(!!d.activo)
  }

  async function guardar() {
    if (!nombre.trim()) return
    setSaving(true)
    setError(null)
    try {
      if (editingId === 'new') {
        await api.post('/api/depositos', { nombre, descripcion })
      } else if (editingId) {
        await api.put(`/api/depositos/${editingId}`, { nombre, descripcion, activo: activoEdit })
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
    if (!window.confirm(`¿Eliminar el depósito «${d.nombre}»?`)) return
    setError(null)
    try {
      await api.del(`/api/depositos/${d.id}`)
      if (verStockId === d.id) setVerStockId(null)
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
        cantidad: Number(cantidad), fecha: fechaTransf, observaciones,
      })
      setCantidad('')
      setObservaciones('')
      await load()
      if (productoId) api.get<StockPorDeposito[]>(`/api/depositos/stock-producto/${productoId}`).then(setStockOrigen)
      if (verStockId === Number(origenId) || verStockId === Number(destinoId)) {
        api.get<StockItem[]>(`/api/depositos/${verStockId}/stock`).then(setStockDeposito).catch(() => {})
      }
    } catch (err) {
      setError(describeError(err))
    } finally {
      setTransfiriendo(false)
    }
  }

  const estadoStock = (s: StockItem): { label: string; className: string } => {
    if (s.stock_actual <= 0) return { label: 'Sin stock', className: 'border-destructive/30 bg-destructive/10 text-destructive' }
    if (s.stock_minimo > 0 && s.stock_actual < s.stock_minimo) return { label: 'Bajo mínimo', className: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400' }
    return { label: 'OK', className: 'border-emerald-600/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' }
  }
  const depositoAbierto = depositos.find((d) => d.id === verStockId)

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Building2 className="size-5" />Depósitos</h2>
        <div className="flex items-center gap-2">
          {editingId === null && <Button variant="outline" onClick={() => document.getElementById('transferir-stock')?.scrollIntoView({ behavior: 'smooth' })}><ArrowLeftRight />Transferir stock</Button>}
          {editingId === null && <Button onClick={startCreate}><Plus />Nuevo depósito</Button>}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {editingId !== null && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {editingId === 'new' ? 'Nuevo depósito' : `Editar: ${depositos.find((d) => d.id === editingId)?.nombre ?? ''}`}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5"><Label>Nombre</Label><Input value={nombre} onChange={(e) => setNombre(e.target.value)} className="w-48" /></div>
            <div className="grid gap-1.5"><Label>Descripción</Label><Input value={descripcion} onChange={(e) => setDescripcion(e.target.value)} className="w-64" placeholder="Ej: Almacén norte, Depósito de materias primas…" /></div>
            {editingId !== 'new' && (
              <label className="flex items-center gap-2 pb-2 text-sm">
                <input type="checkbox" checked={activoEdit} onChange={(e) => setActivoEdit(e.target.checked)} />Activo
              </label>
            )}
            <Button disabled={saving} onClick={guardar}><Check />{saving ? 'Guardando…' : 'Guardar'}</Button>
            <Button type="button" variant="outline" onClick={() => setEditingId(null)}>Cancelar</Button>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : depositos.length === 0 ? (
        <Card><CardContent className="py-6 text-center text-sm text-muted-foreground">No hay depósitos creados.</CardContent></Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {depositos.map((d) => (
            <Card key={d.id} className={d.activo ? '' : 'opacity-50'}>
              <CardContent className="grid gap-3">
                <div>
                  <p className="flex items-center gap-2 font-semibold"><Building2 className="size-4 text-primary" />{d.nombre}</p>
                  <div className="mt-1 flex gap-1.5">
                    {d.es_default && <Badge variant="default">Por defecto</Badge>}
                    {!d.activo && <Badge variant="secondary">Inactivo</Badge>}
                  </div>
                </div>
                {d.descripcion && <p className="text-sm text-muted-foreground">{d.descripcion}</p>}
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Package className="size-4" />{d.total_productos} producto{d.total_productos !== 1 ? 's' : ''} con stock
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => setVerStockId(verStockId === d.id ? null : d.id)}>
                    <Eye />{verStockId === d.id ? 'Ocultar' : 'Ver stock'}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => startEdit(d)}><Pencil />Editar</Button>
                  {!d.es_default && (
                    <>
                      <Button size="sm" variant="outline" title="Usar como depósito por defecto" onClick={() => setDefault(d)}><Star />Predeterminar</Button>
                      <Button size="sm" variant="outline" onClick={() => eliminar(d)}><Trash2 /></Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {depositoAbierto && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              <span className="flex items-center gap-2">
                Stock en {depositoAbierto.nombre}
                {depositoAbierto.es_default ? <Badge variant="secondary">Por defecto</Badge> : null}
              </span>
              <span className="text-sm font-normal text-muted-foreground">{stockDeposito.length} productos</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {stockLoading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
            ) : stockDeposito.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Este depósito no tiene stock registrado.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b text-muted-foreground">
                  <tr>
                    <th className="p-3 text-left font-medium">Código</th>
                    <th className="p-3 text-left font-medium">Producto</th>
                    <th className="p-3 text-left font-medium">Categoría</th>
                    <th className="p-3 text-center font-medium">Unidad</th>
                    <th className="p-3 text-right font-medium">Stock actual</th>
                    <th className="p-3 text-right font-medium">Stock mínimo</th>
                    <th className="p-3 text-center font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {stockDeposito.map((s) => {
                    const estado = estadoStock(s)
                    return (
                      <tr key={s.id} className="border-b last:border-0">
                        <td className="p-3 text-muted-foreground">{s.codigo || '—'}</td>
                        <td className="p-3 font-medium">{s.nombre}</td>
                        <td className="p-3 text-muted-foreground">{s.categoria || '—'}</td>
                        <td className="p-3 text-center">{s.unidad}</td>
                        <td className="p-3 text-right font-semibold">{s.stock_actual}</td>
                        <td className="p-3 text-right text-muted-foreground">{s.stock_minimo}</td>
                        <td className="p-3 text-center"><Badge variant="outline" className={estado.className}>{estado.label}</Badge></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}

      <Card id="transferir-stock">
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><ArrowLeftRight className="size-4" />Transferir stock entre depósitos</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid gap-1.5 max-w-sm">
            <Label>Producto</Label>
            <Select value={productoId} onValueChange={setProductoId}>
              <SelectTrigger><SelectValue placeholder="Elegir producto…" /></SelectTrigger>
              <SelectContent>
                {productos.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.nombre}{p.codigo ? ` (${p.codigo})` : ''}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {stockOrigen.length > 0 && (
            <div className="rounded-md border bg-muted/40 p-3 text-sm">
              <p className="mb-1 flex items-center gap-1.5 font-medium text-muted-foreground"><Info className="size-4" />Stock disponible por depósito:</p>
              <ul className="flex flex-wrap gap-x-4 gap-y-1">
                {stockOrigen.map((s) => (
                  <li key={s.id}>{s.nombre}{s.es_default ? ' ★' : ''}: <span className="font-medium text-foreground">{s.stock_actual}</span></li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5">
              <Label>Depósito origen</Label>
              <Select value={origenId} onValueChange={setOrigenId}>
                <SelectTrigger className="w-40"><SelectValue placeholder="Origen…" /></SelectTrigger>
                <SelectContent>
                  {depositos.filter((d) => d.activo).map((d) => <SelectItem key={d.id} value={String(d.id)}>{d.nombre}{d.es_default ? ' ★' : ''}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label>Depósito destino</Label>
              <Select value={destinoId} onValueChange={setDestinoId}>
                <SelectTrigger className="w-40"><SelectValue placeholder="Destino…" /></SelectTrigger>
                <SelectContent>
                  {depositos.filter((d) => d.activo).map((d) => <SelectItem key={d.id} value={String(d.id)}>{d.nombre}{d.es_default ? ' ★' : ''}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5"><Label>Cantidad</Label><Input type="number" step="0.01" value={cantidad} onChange={(e) => setCantidad(e.target.value)} className="w-28" /></div>
            <div className="grid gap-1.5"><Label>Fecha</Label><Input type="date" value={fechaTransf} onChange={(e) => setFechaTransf(e.target.value)} className="w-40" /></div>
            <div className="grid gap-1.5"><Label>Observaciones</Label><Input value={observaciones} onChange={(e) => setObservaciones(e.target.value)} placeholder="Opcional" className="w-48" /></div>
            <Button disabled={transfiriendo || !productoId || !origenId || !destinoId || !cantidad} onClick={transferir}>
              <ArrowLeftRight />{transfiriendo ? 'Transfiriendo…' : 'Confirmar transferencia'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
