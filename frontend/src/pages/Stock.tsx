import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type MovimientoStock, type StockItem } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  Boxes, AlertTriangle, Pencil, History, RefreshCw, ArrowDownToLine, ArrowUpFromLine,
  ShoppingCart, RotateCcw, X,
} from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

const TIPO_LABELS: Record<string, string> = { entrada: 'Entrada', salida: 'Salida', ajuste: 'Ajuste', venta: 'Venta' }

function TipoBadge({ tipo }: { tipo: string }) {
  if (tipo === 'entrada') {
    return <Badge className="bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-400"><ArrowDownToLine />Entrada</Badge>
  }
  if (tipo === 'salida') {
    return <Badge variant="destructive"><ArrowUpFromLine />Salida</Badge>
  }
  if (tipo === 'venta') {
    return <Badge><ShoppingCart />Venta</Badge>
  }
  if (tipo === 'ajuste') {
    return <Badge variant="secondary"><RotateCcw />Ajuste</Badge>
  }
  return <Badge variant="outline">{TIPO_LABELS[tipo] ?? tipo}</Badge>
}

function EstadoBadge({ p }: { p: StockItem }) {
  const critico = p.stock_actual <= 0
  const bajo = p.stock_minimo > 0 && p.stock_actual <= p.stock_minimo
  if (critico) return <Badge variant="destructive">Sin stock</Badge>
  if (bajo) return <Badge className="bg-amber-500/15 text-amber-700 hover:bg-amber-500/15 dark:text-amber-400">Bajo mínimo</Badge>
  return <Badge className="bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-400">OK</Badge>
}

export function Stock() {
  const [productos, setProductos] = useState<StockItem[]>([])
  const [alertas, setAlertas] = useState<StockItem[]>([])
  const [movimientos, setMovimientos] = useState<MovimientoStock[]>([])
  const [loading, setLoading] = useState(true)
  const [movLoading, setMovLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [movFiltroProducto, setMovFiltroProducto] = useState('')
  const [movDesde, setMovDesde] = useState('')
  const [movHasta, setMovHasta] = useState('')

  const [ajustandoId, setAjustandoId] = useState<number | null>(null)
  const [modo, setModo] = useState('absoluto')
  const [cantidad, setCantidad] = useState('')
  const [fecha, setFecha] = useState(todayIso())
  const [referencia, setReferencia] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    cargarMovimientos()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [movFiltroProducto, movDesde, movHasta])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ productos: StockItem[]; alertas: StockItem[] }>('/api/stock')
      setProductos(data.productos)
      setAlertas(data.alertas)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function cargarMovimientos() {
    setMovLoading(true)
    try {
      const params = new URLSearchParams()
      if (movFiltroProducto) params.set('producto_id', movFiltroProducto)
      if (movDesde) params.set('desde', movDesde)
      if (movHasta) params.set('hasta', movHasta)
      const qs = params.toString()
      const data = await api.get<MovimientoStock[]>(`/api/stock/movimientos${qs ? `?${qs}` : ''}`)
      setMovimientos(data)
    } catch {
      // el listado de movimientos no es critico para la pantalla principal
    } finally {
      setMovLoading(false)
    }
  }

  function verMovimientos(p: StockItem) {
    setMovFiltroProducto(String(p.id))
  }

  function limpiarFiltroMovimientos() {
    setMovFiltroProducto('')
    setMovDesde('')
    setMovHasta('')
  }

  function startAjuste(p: StockItem) {
    setAjustandoId(p.id)
    setModo('absoluto')
    setCantidad(String(p.stock_actual))
    setFecha(todayIso())
    setReferencia('')
  }

  function cambiarModo(nuevoModo: string, stockActualDelProducto: number) {
    setModo(nuevoModo)
    if (nuevoModo === 'absoluto') setCantidad(String(stockActualDelProducto))
    else setCantidad('')
  }

  async function guardarAjuste() {
    if (ajustandoId === null) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/stock/${ajustandoId}/ajuste`, {
        modo, cantidad: Number(cantidad), referencia, fecha,
      })
      setAjustandoId(null)
      await load()
      await cargarMovimientos()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  const columns = useMemo<ColumnDef<StockItem>[]>(() => [
    { accessorKey: 'codigo', header: 'Código', cell: ({ row }) => <span className="font-mono text-xs">{row.original.codigo || '—'}</span> },
    { accessorKey: 'nombre', header: sortableHeader('Producto'), cell: ({ row }) => <span className="font-medium">{row.original.nombre}</span> },
    { accessorKey: 'categoria', header: 'Categoría', cell: ({ row }) => row.original.categoria || '—' },
    { accessorKey: 'unidad', header: 'Unidad', cell: ({ row }) => <span className="text-muted-foreground">{row.original.unidad}</span> },
    { accessorKey: 'stock_minimo', header: 'Mínimo', cell: ({ row }) => row.original.stock_minimo > 0 ? row.original.stock_minimo : '—' },
    {
      accessorKey: 'stock_actual',
      header: 'Stock actual',
      cell: ({ row }) => {
        const critico = row.original.stock_actual <= 0
        const bajo = row.original.stock_minimo > 0 && row.original.stock_actual <= row.original.stock_minimo
        const cls = critico ? 'font-semibold text-destructive' : bajo ? 'font-semibold text-amber-600 dark:text-amber-400' : 'font-semibold text-emerald-600 dark:text-emerald-400'
        return <span className={cls}>{row.original.stock_actual} {row.original.unidad}</span>
      },
    },
    { id: 'estado', header: 'Estado', cell: ({ row }) => <EstadoBadge p={row.original} /> },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => verMovimientos(row.original)} title="Ver movimientos"><History />Movimientos</Button>
          <Button size="sm" variant="outline" onClick={() => startAjuste(row.original)}><Pencil />Ajustar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  const movColumns = useMemo<ColumnDef<MovimientoStock>[]>(() => [
    { accessorKey: 'fecha', header: sortableHeader('Fecha') },
    { accessorKey: 'producto_nombre', header: 'Producto' },
    { accessorKey: 'tipo', header: 'Tipo', cell: ({ row }) => <TipoBadge tipo={row.original.tipo} /> },
    {
      accessorKey: 'cantidad',
      header: 'Cantidad',
      cell: ({ row }) => (
        <span className={row.original.cantidad >= 0 ? 'font-medium text-emerald-600 dark:text-emerald-400' : 'font-medium text-destructive'}>
          {row.original.cantidad >= 0 ? '+' : ''}{row.original.cantidad} {row.original.unidad}
        </span>
      ),
    },
    { accessorKey: 'referencia', header: 'Referencia', cell: ({ row }) => row.original.referencia || '—' },
  ], [])

  const productoAjustando = productos.find((p) => p.id === ajustandoId)

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold"><Boxes className="size-5 text-primary" />Stock</h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {alertas.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-base text-destructive"><AlertTriangle className="size-4" />{alertas.length} producto{alertas.length > 1 ? 's' : ''} con stock bajo mínimo</CardTitle></CardHeader>
          <CardContent>
            <ul className="flex flex-wrap gap-2">
              {alertas.map((a) => (
                <li key={a.id}><Badge className="bg-amber-500/15 text-amber-700 hover:bg-amber-500/15 dark:text-amber-400">{a.nombre}: {a.stock_actual} {a.unidad}</Badge></li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {ajustandoId !== null && (
        <Card>
          <CardHeader><CardTitle className="text-base">Ajustar stock — {productoAjustando?.nombre}</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5">
              <Label>Modo</Label>
              <Select value={modo} onValueChange={(v) => cambiarModo(v, productoAjustando?.stock_actual ?? 0)}>
                <SelectTrigger className="w-52"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="absoluto"><RefreshCw />Fijar valor absoluto</SelectItem>
                  <SelectItem value="entrada"><ArrowDownToLine />Sumar entrada</SelectItem>
                  <SelectItem value="salida"><ArrowUpFromLine />Restar salida</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label>{modo === 'absoluto' ? `Stock nuevo (${productoAjustando?.unidad ?? ''})` : modo === 'entrada' ? `Cantidad a ingresar (${productoAjustando?.unidad ?? ''})` : `Cantidad a retirar (${productoAjustando?.unidad ?? ''})`}</Label>
              <Input type="number" step="0.01" value={cantidad} onChange={(e) => setCantidad(e.target.value)} className="w-40" />
            </div>
            <div className="grid gap-1.5"><Label>Fecha</Label><Input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="w-40" /></div>
            <div className="grid gap-1.5"><Label>Motivo / Referencia</Label><Input value={referencia} onChange={(e) => setReferencia(e.target.value)} className="w-56" placeholder="Ej: Compra, conteo físico, rotura…" /></div>
            <Button disabled={saving} onClick={guardarAjuste}>{saving ? 'Guardando…' : 'Guardar movimiento'}</Button>
            <Button type="button" variant="outline" onClick={() => setAjustandoId(null)}>Cancelar</Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={productos} emptyMessage="Sin productos activos." />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex items-center justify-between space-y-0">
          <CardTitle className="flex items-center gap-2 text-base"><History className="size-4" />Historial de movimientos</CardTitle>
          <div className="flex flex-wrap items-end gap-2">
            <Select value={movFiltroProducto || 'todos'} onValueChange={(v) => setMovFiltroProducto(v === 'todos' ? '' : v)}>
              <SelectTrigger className="w-48"><SelectValue placeholder="Todos los productos" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todos los productos</SelectItem>
                {productos.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.nombre}</SelectItem>)}
              </SelectContent>
            </Select>
            <Input type="date" value={movDesde} onChange={(e) => setMovDesde(e.target.value)} className="w-36" />
            <Input type="date" value={movHasta} onChange={(e) => setMovHasta(e.target.value)} className="w-36" />
            {(movFiltroProducto || movDesde || movHasta) && (
              <Button size="sm" variant="ghost" onClick={limpiarFiltroMovimientos}><X />Limpiar</Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {movLoading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={movColumns} data={movimientos} emptyMessage="Sin movimientos registrados." />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
