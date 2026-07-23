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

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

const TIPO_LABELS: Record<string, string> = { entrada: 'Entrada', salida: 'Salida', ajuste: 'Ajuste', venta: 'Venta' }

export function Stock() {
  const [productos, setProductos] = useState<StockItem[]>([])
  const [alertas, setAlertas] = useState<StockItem[]>([])
  const [movimientos, setMovimientos] = useState<MovimientoStock[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [ajustandoId, setAjustandoId] = useState<number | null>(null)
  const [modo, setModo] = useState('absoluto')
  const [cantidad, setCantidad] = useState('')
  const [referencia, setReferencia] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    load()
    api.get<MovimientoStock[]>('/api/stock/movimientos').then(setMovimientos).catch(() => {})
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

  function startAjuste(p: StockItem) {
    setAjustandoId(p.id)
    setModo('absoluto')
    setCantidad(String(p.stock_actual))
    setReferencia('')
  }

  async function guardarAjuste() {
    if (ajustandoId === null) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/stock/${ajustandoId}/ajuste`, {
        modo, cantidad: Number(cantidad), referencia, fecha: todayIso(),
      })
      setAjustandoId(null)
      await load()
      api.get<MovimientoStock[]>('/api/stock/movimientos').then(setMovimientos)
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
    {
      accessorKey: 'stock_actual',
      header: 'Stock actual',
      cell: ({ row }) => {
        const bajo = row.original.stock_minimo > 0 && row.original.stock_actual <= row.original.stock_minimo
        return <span className={bajo ? 'font-medium text-destructive' : 'font-medium'}>{row.original.stock_actual} {row.original.unidad}</span>
      },
    },
    { accessorKey: 'stock_minimo', header: 'Mínimo' },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end">
          <Button size="sm" variant="outline" onClick={() => startAjuste(row.original)}>Ajustar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  const movColumns = useMemo<ColumnDef<MovimientoStock>[]>(() => [
    { accessorKey: 'fecha', header: sortableHeader('Fecha') },
    { accessorKey: 'producto_nombre', header: 'Producto' },
    { accessorKey: 'tipo', header: 'Tipo', cell: ({ row }) => TIPO_LABELS[row.original.tipo] ?? row.original.tipo },
    {
      accessorKey: 'cantidad',
      header: 'Cantidad',
      cell: ({ row }) => (
        <span className={row.original.cantidad >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}>
          {row.original.cantidad >= 0 ? '+' : ''}{row.original.cantidad} {row.original.unidad}
        </span>
      ),
    },
    { accessorKey: 'referencia', header: 'Referencia', cell: ({ row }) => row.original.referencia || '—' },
  ], [])

  return (
    <div className="grid gap-4">
      <h2 className="text-lg font-semibold">Stock</h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {alertas.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-base text-destructive">Alertas de stock bajo</CardTitle></CardHeader>
          <CardContent>
            <ul className="flex flex-wrap gap-2">
              {alertas.map((a) => (
                <li key={a.id}><Badge variant="destructive">{a.nombre}: {a.stock_actual} {a.unidad}</Badge></li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {ajustandoId !== null && (
        <Card>
          <CardHeader><CardTitle className="text-base">Ajustar stock — {productos.find((p) => p.id === ajustandoId)?.nombre}</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5">
              <Label>Modo</Label>
              <Select value={modo} onValueChange={setModo}>
                <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="absoluto">Fijar valor absoluto</SelectItem>
                  <SelectItem value="entrada">Sumar entrada</SelectItem>
                  <SelectItem value="salida">Restar salida</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5"><Label>Cantidad</Label><Input type="number" step="0.01" value={cantidad} onChange={(e) => setCantidad(e.target.value)} className="w-32" /></div>
            <div className="grid gap-1.5"><Label>Referencia</Label><Input value={referencia} onChange={(e) => setReferencia(e.target.value)} className="w-52" placeholder="Ajuste manual" /></div>
            <Button disabled={saving} onClick={guardarAjuste}>{saving ? 'Guardando…' : 'Guardar'}</Button>
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
        <CardHeader><CardTitle className="text-base">Movimientos recientes</CardTitle></CardHeader>
        <CardContent>
          <DataTable columns={movColumns} data={movimientos} emptyMessage="Sin movimientos todavía." />
        </CardContent>
      </Card>
    </div>
  )
}
