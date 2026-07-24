import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, type CategoriaEgreso, type Egreso, type ResumenEgresos,
} from '../api'
import { Card, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  ArrowUpCircle, CheckCircle2, Eye, Filter, Hourglass, Plus, X,
} from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function firstOfMonthIso(): string {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

// Alta y detalle ahora viven en páginas propias (EgresoNuevo.tsx,
// EgresoDetalle.tsx), igual que web/templates/egresos/list.html enlazaba a
// /egresos/nuevo y /egresos/{id}. Esta página queda solo como listado.
export function Egresos() {
  const [desde, setDesde] = useState(firstOfMonthIso())
  const [hasta, setHasta] = useState(todayIso())
  const [categoriaFiltro, setCategoriaFiltro] = useState('')
  const [estadoFiltro, setEstadoFiltro] = useState('')
  const [egresos, setEgresos] = useState<Egreso[]>([])
  const [resumen, setResumen] = useState<ResumenEgresos | null>(null)
  const [categorias, setCategorias] = useState<CategoriaEgreso[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<CategoriaEgreso[]>('/api/egresos/categorias').then(setCategorias).catch(() => {})
  }, [])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desde, hasta, categoriaFiltro, estadoFiltro])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ desde, hasta })
      if (categoriaFiltro) params.set('categoria', categoriaFiltro)
      if (estadoFiltro) params.set('estado', estadoFiltro)
      const data = await api.get<{ items: Egreso[]; resumen: ResumenEgresos }>(
        `/api/egresos?${params.toString()}`,
      )
      setEgresos(data.items)
      setResumen(data.resumen)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function limpiarFiltros() {
    setCategoriaFiltro('')
    setEstadoFiltro('')
  }

  const estadoBadgeClass: Record<Egreso['estado'], string> = {
    pagado: 'bg-emerald-600 text-white [a&]:hover:bg-emerald-600/90 dark:bg-emerald-500',
    parcial: 'bg-amber-500 text-white [a&]:hover:bg-amber-500/90 dark:bg-amber-600',
    pendiente: '',
  }
  const estadoVariant: Record<Egreso['estado'], 'default' | 'secondary' | 'outline'> = {
    pagado: 'default', parcial: 'default', pendiente: 'secondary',
  }
  const estadoLabel: Record<Egreso['estado'], string> = {
    pagado: 'Pagado', parcial: 'Parcial', pendiente: 'Pendiente',
  }

  const columns = useMemo<ColumnDef<Egreso>[]>(() => [
    { accessorKey: 'fecha', header: sortableHeader('Fecha') },
    { accessorKey: 'proveedor_nombre', header: 'Proveedor', cell: ({ row }) => row.original.proveedor_nombre || '—' },
    { accessorKey: 'concepto', header: 'Concepto', cell: ({ row }) => <span className="font-medium">{row.original.concepto}</span> },
    { accessorKey: 'categoria', header: 'Categoría', cell: ({ row }) => row.original.categoria || '—' },
    {
      id: 'comprobante',
      header: 'Comprobante',
      cell: ({ row }) => row.original.numero ? <span className="font-mono text-sm">{row.original.numero}</span> : '—',
    },
    {
      accessorKey: 'estado',
      header: 'Estado',
      cell: ({ row }) => (
        <Badge variant={estadoVariant[row.original.estado]} className={estadoBadgeClass[row.original.estado]}>
          {estadoLabel[row.original.estado]}
        </Badge>
      ),
    },
    { accessorKey: 'total', header: 'Total', cell: ({ row }) => <span className="font-medium text-destructive">{formatCurrency(row.original.total)}</span> },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button asChild size="sm" variant="outline"><Link to={`/egresos/${row.original.id}`}><Eye />Ver</Link></Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <ArrowUpCircle className="size-5 text-destructive" />Egresos
        </h2>
        <Button asChild><Link to="/egresos/nuevo"><Plus />Nuevo egreso</Link></Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {resumen && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card><CardContent className="flex items-start justify-between gap-3">
            <div><CardDescription>Total del período</CardDescription><p className="text-2xl font-bold">{formatCurrency(resumen.total_periodo)}</p></div>
            <span className="shrink-0 rounded-lg bg-muted p-2 text-muted-foreground"><ArrowUpCircle /></span>
          </CardContent></Card>
          <Card><CardContent className="flex items-start justify-between gap-3">
            <div><CardDescription>Pagado</CardDescription><p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(resumen.pagado)}</p></div>
            <span className="shrink-0 rounded-lg bg-emerald-500/10 p-2 text-emerald-600 dark:text-emerald-400"><CheckCircle2 /></span>
          </CardContent></Card>
          <Card><CardContent className="flex items-start justify-between gap-3">
            <div><CardDescription>Pendiente / Parcial</CardDescription><p className="text-2xl font-bold text-destructive">{formatCurrency(resumen.pendiente)}</p></div>
            <span className="shrink-0 rounded-lg bg-destructive/10 p-2 text-destructive"><Hourglass /></span>
          </CardContent></Card>
        </div>
      )}

      <Card>
        <CardContent className="flex flex-wrap items-end gap-3 py-3">
          <div className="grid gap-1.5">
            <Label>Desde</Label>
            <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="w-40" />
          </div>
          <div className="grid gap-1.5">
            <Label>Hasta</Label>
            <Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="w-40" />
          </div>
          <div className="grid gap-1.5">
            <Label>Categoría</Label>
            <Select value={categoriaFiltro || '__todas__'} onValueChange={(v) => setCategoriaFiltro(v === '__todas__' ? '' : v)}>
              <SelectTrigger className="w-48"><SelectValue placeholder="Todas las categorías" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__todas__">Todas las categorías</SelectItem>
                {categorias.map((c) => <SelectItem key={c.id} value={c.nombre}>{c.nombre}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label>Estado</Label>
            <Select value={estadoFiltro || '__todos__'} onValueChange={(v) => setEstadoFiltro(v === '__todos__' ? '' : v)}>
              <SelectTrigger className="w-40"><SelectValue placeholder="Todos los estados" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__todos__">Todos los estados</SelectItem>
                <SelectItem value="pendiente">Pendiente</SelectItem>
                <SelectItem value="parcial">Parcial</SelectItem>
                <SelectItem value="pagado">Pagado</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button size="sm" variant="outline" onClick={load} title="Filtrar"><Filter /></Button>
          {(categoriaFiltro || estadoFiltro) && (
            <Button size="sm" variant="ghost" onClick={limpiarFiltros} title="Limpiar filtros"><X />Limpiar</Button>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={egresos} emptyMessage="Sin egresos en el período." />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
