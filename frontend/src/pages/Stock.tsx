import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
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
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogClose,
} from '@/components/ui/dialog'
import { DataTable, sortableHeader } from 'libra-ui/data-table'
import { formatEntero } from '@/lib/utils'
import {
  Archive, AlertTriangle, Pencil, History, RefreshCw, ArrowDownToLine, ArrowUpFromLine,
  ShoppingCart, RotateCcw, X, Filter,
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

const MODOS_AJUSTE = [
  { value: 'absoluto', label: 'Fijar en…', icon: RefreshCw },
  { value: 'entrada', label: 'Entrada', icon: ArrowDownToLine },
  { value: 'salida', label: 'Salida', icon: ArrowUpFromLine },
]

export function Stock() {
  const [productos, setProductos] = useState<StockItem[]>([])
  const [alertas, setAlertas] = useState<StockItem[]>([])
  const [movimientos, setMovimientos] = useState<MovimientoStock[]>([])
  const [loading, setLoading] = useState(true)
  const [movLoading, setMovLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [movimientosVisible, setMovimientosVisible] = useState(false)
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

  function toggleMovimientos() {
    setMovimientosVisible((v) => {
      const next = !v
      if (next) cargarMovimientos()
      return next
    })
  }

  function verMovimientos(p: StockItem) {
    setMovFiltroProducto(String(p.id))
    setMovimientosVisible(true)
    setMovLoading(true)
    setTimeout(cargarMovimientos, 0)
  }

  function limpiarFiltroMovimientos() {
    setMovFiltroProducto('')
    setMovDesde('')
    setMovHasta('')
    setTimeout(cargarMovimientos, 0)
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
      if (movimientosVisible) await cargarMovimientos()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  const columns = useMemo<ColumnDef<StockItem>[]>(() => [
    {
      accessorKey: 'nombre',
      header: sortableHeader('Producto'),
      size: 200,
      minSize: 110,
      meta: { stretch: true },
      cell: ({ row }) => (
        <span className="block truncate" title={row.original.nombre}>
          <span className="font-semibold">{row.original.nombre}</span>
          {row.original.codigo && <span className="ml-1 text-sm text-muted-foreground">· {row.original.codigo}</span>}
        </span>
      ),
    },
    { accessorKey: 'categoria', header: 'Categoría', size: 120, minSize: 90, cell: ({ row }) => <span className="block truncate text-muted-foreground" title={row.original.categoria ?? undefined}>{row.original.categoria || '—'}</span> },
    { accessorKey: 'unidad', header: 'Unidad', size: 85, minSize: 70, cell: ({ row }) => <span className="block truncate text-muted-foreground">{row.original.unidad}</span> },
    { accessorKey: 'stock_minimo', header: () => <div className="text-right">Stock mínimo</div>, size: 115, minSize: 95, cell: ({ row }) => <div className="truncate text-right">{row.original.stock_minimo > 0 ? formatEntero(row.original.stock_minimo) : '—'}</div> },
    {
      accessorKey: 'stock_actual',
      header: () => <div className="text-right">Stock actual</div>,
      size: 115,
      minSize: 95,
      cell: ({ row }) => {
        const critico = row.original.stock_actual <= 0
        const bajo = row.original.stock_minimo > 0 && row.original.stock_actual <= row.original.stock_minimo
        const cls = critico ? 'font-bold text-lg text-destructive' : bajo ? 'font-bold text-lg text-amber-600 dark:text-amber-400' : 'font-bold text-lg text-emerald-600 dark:text-emerald-400'
        return <div className={`truncate text-right ${cls}`}>{formatEntero(row.original.stock_actual)}</div>
      },
    },
    { id: 'estado', header: 'Estado', size: 125, minSize: 95, cell: ({ row }) => <EstadoBadge p={row.original} /> },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      size: 92,
      minSize: 84,
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          <Button size="icon" variant="outline" onClick={() => verMovimientos(row.original)} title="Ver movimientos" aria-label="Ver movimientos"><History /></Button>
          <Button size="icon" variant="outline" onClick={() => startAjuste(row.original)} title="Ajustar stock" aria-label="Ajustar stock"><Pencil /></Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  const movColumns = useMemo<ColumnDef<MovimientoStock>[]>(() => [
    { accessorKey: 'fecha', header: 'Fecha' },
    {
      accessorKey: 'producto_nombre',
      header: 'Producto',
      cell: ({ row }) => (
        <button type="button" className="font-semibold hover:underline" onClick={() => verMovimientos({ id: row.original.producto_id } as StockItem)}>
          {row.original.producto_nombre}
        </button>
      ),
    },
    { accessorKey: 'tipo', header: 'Tipo', cell: ({ row }) => <TipoBadge tipo={row.original.tipo} /> },
    {
      accessorKey: 'cantidad',
      header: 'Cantidad',
      cell: ({ row }) => (
        <span className={row.original.cantidad >= 0 ? 'font-semibold text-emerald-600 dark:text-emerald-400' : 'font-semibold text-destructive'}>
          {row.original.cantidad >= 0 ? '+' : ''}{formatEntero(row.original.cantidad)}
        </span>
      ),
    },
    { accessorKey: 'referencia', header: 'Referencia', cell: ({ row }) => <span className="text-muted-foreground">{row.original.referencia || '—'}</span> },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  const productoAjustando = productos.find((p) => p.id === ajustandoId)

  // Preview en vivo del stock resultante, igual que calcResultado() en el
  // stock/ajuste.html viejo: toma el stock actual del producto (fijo al
  // abrir el ajuste) y aplica el modo sobre la cantidad tipeada.
  function resultadoAjuste(): number | null {
    if (!productoAjustando) return null
    const val = parseFloat(cantidad) || 0
    const base = productoAjustando.stock_actual
    if (modo === 'absoluto') return val
    if (modo === 'entrada') return base + val
    return base - val
  }
  const resultado = resultadoAjuste()

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Archive className="size-5 text-primary" />Stock</h2>
        <Button variant="outline" onClick={toggleMovimientos}><History />Historial de movimientos</Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {alertas.length > 0 && (
        <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/40">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" />
          <p>
            <strong>{alertas.length} producto{alertas.length > 1 ? 's' : ''} con stock bajo mínimo:</strong>{' '}
            {alertas.map((a) => (
              <Badge key={a.id} className="ml-1 bg-amber-500/15 text-amber-700 hover:bg-amber-500/15 dark:text-amber-400">{a.nombre} ({formatEntero(a.stock_actual)} {a.unidad})</Badge>
            ))}
          </p>
        </div>
      )}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable
              columns={columns}
              data={productos}
              emptyMessage={<>No hay productos activos. <Link to="/productos" className="text-primary hover:underline">Crear un producto</Link>.</>}
            />
          )}
        </CardContent>
      </Card>

      <Dialog open={ajustandoId !== null} onOpenChange={(o) => { if (!o) setAjustandoId(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Pencil className="size-4" />Ajuste de stock — {productoAjustando?.nombre}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="flex gap-4">
              <div className="text-center">
                <div className={`text-3xl font-bold ${(productoAjustando?.stock_actual ?? 0) <= 0 ? 'text-destructive' : (productoAjustando?.stock_minimo ?? 0) > 0 && (productoAjustando?.stock_actual ?? 0) <= (productoAjustando?.stock_minimo ?? 0) ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                  {formatEntero(productoAjustando?.stock_actual ?? 0)}
                </div>
                <div className="text-sm text-muted-foreground">Stock actual ({productoAjustando?.unidad})</div>
              </div>
              {(productoAjustando?.stock_minimo ?? 0) > 0 && (
                <div className="text-center">
                  <div className="text-3xl font-bold text-muted-foreground">{formatEntero(productoAjustando?.stock_minimo ?? 0)}</div>
                  <div className="text-sm text-muted-foreground">Mínimo</div>
                </div>
              )}
            </div>

            <div className="grid gap-1.5">
              <Label>Tipo de ajuste</Label>
              <div className="flex flex-wrap gap-2">
                {MODOS_AJUSTE.map((m) => (
                  <Button
                    key={m.value}
                    type="button"
                    size="sm"
                    variant={modo === m.value ? 'default' : 'outline'}
                    onClick={() => cambiarModo(m.value, productoAjustando?.stock_actual ?? 0)}
                  >
                    <m.icon />{m.label}
                  </Button>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap items-end gap-3">
              <div className="grid gap-1.5">
                <Label>{modo === 'absoluto' ? `Stock nuevo (${productoAjustando?.unidad ?? ''})` : modo === 'entrada' ? `Cantidad a ingresar (${productoAjustando?.unidad ?? ''})` : `Cantidad a retirar (${productoAjustando?.unidad ?? ''})`}</Label>
                <Input type="number" step="0.01" value={cantidad} onChange={(e) => setCantidad(e.target.value)} className="w-40" />
              </div>
              <div className="grid gap-1.5"><Label>Fecha</Label><Input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="w-40" /></div>
              <div className="grid gap-1.5"><Label>Motivo / Referencia</Label><Input value={referencia} onChange={(e) => setReferencia(e.target.value)} className="w-56" placeholder="Ej: Compra, conteo físico, rotura…" /></div>
            </div>
            {resultado !== null && (
              <p className={`text-sm ${resultado < 0 ? 'text-destructive' : 'text-emerald-600 dark:text-emerald-400'}`}>
                Stock resultante: {resultado.toFixed(3)} {productoAjustando?.unidad}
              </p>
            )}
          </div>
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Cancelar</Button></DialogClose>
            <Button disabled={saving} onClick={guardarAjuste}>{saving ? 'Guardando…' : 'Guardar movimiento'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {movimientosVisible && (
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-base"><History className="size-4" />Movimientos de stock</CardTitle></CardHeader>
          <CardContent className="grid gap-3">
            <div className="flex flex-wrap items-end gap-2">
              <Select value={movFiltroProducto || 'todos'} onValueChange={(v) => setMovFiltroProducto(v === 'todos' ? '' : v)}>
                <SelectTrigger className="w-56"><SelectValue placeholder="— Todos los productos —" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">— Todos los productos —</SelectItem>
                  {productos.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
              <Input type="date" value={movDesde} onChange={(e) => setMovDesde(e.target.value)} className="w-40" />
              <Input type="date" value={movHasta} onChange={(e) => setMovHasta(e.target.value)} className="w-40" />
              <Button size="sm" variant="outline" onClick={cargarMovimientos}><Filter />Filtrar</Button>
              {(movFiltroProducto || movDesde || movHasta) && (
                <Button size="sm" variant="outline" onClick={limpiarFiltroMovimientos}><X />Limpiar</Button>
              )}
            </div>
            {movLoading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
            ) : (
              <DataTable columns={movColumns} data={movimientos} emptyMessage="No hay movimientos registrados." />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
