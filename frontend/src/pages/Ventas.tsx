import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, MEDIOS_PAGO_LABELS, type Venta } from '../api'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  ShoppingCart, Plus, Eye, Printer, FileCheck, Ban, ReceiptText, ListChecks,
} from 'lucide-react'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

const estadoVariant: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  cobrada: 'default', parcial: 'secondary', pendiente: 'outline', anulada: 'destructive',
}

const ESTADO_LABELS: Record<string, string> = {
  cobrada: 'Cobrada', parcial: 'Pago parcial', pendiente: 'Pendiente', anulada: 'Anulada',
}
function estadoLabel(estado: string): string {
  return ESTADO_LABELS[estado] ?? estado
}

export function Ventas() {
  const { user } = useAuth()
  const [ventas, setVentas] = useState<Venta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState('todas')
  const [q, setQ] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ tab })
      if (q) params.set('q', q)
      if (desde) params.set('desde', desde)
      if (hasta) params.set('hasta', hasta)
      setVentas(await api.get<Venta[]>(`/api/ventas?${params.toString()}`))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function limpiarFiltros() {
    setQ(''); setDesde(''); setHasta('')
    setTimeout(load, 0)
  }

  async function anular(venta: Venta) {
    setError(null)
    try {
      await api.post(`/api/ventas/${venta.id}/anular`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const columns = useMemo<ColumnDef<Venta>[]>(() => [
    { accessorKey: 'numero', header: sortableHeader('N°'), cell: ({ row }) => <span className="font-mono text-sm font-semibold text-primary">{row.original.numero}</span> },
    { accessorKey: 'fecha', header: 'Fecha' },
    { accessorKey: 'cliente_nombre', header: 'Cliente', cell: ({ row }) => row.original.cliente_nombre || '—' },
    {
      id: 'pagos',
      header: 'Medios de pago',
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          {row.original.pagos.length === 0
            ? null
            : row.original.pagos.map((p, i) => (
              <Badge key={i} variant="outline" className="font-normal">{MEDIOS_PAGO_LABELS[p.medio] ?? p.medio}: {formatCurrency(p.monto)}</Badge>
            ))}
        </div>
      ),
    },
    { accessorKey: 'total', header: 'Total', cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.total)}</span> },
    {
      accessorKey: 'estado',
      header: 'Estado',
      cell: ({ row }) => <Badge variant={estadoVariant[row.original.estado] ?? 'outline'}>{estadoLabel(row.original.estado)}</Badge>,
    },
    {
      id: 'factura',
      header: 'Factura',
      cell: ({ row }) => row.original.factura_display
        ? <a href={`/facturas/${row.original.factura_id}`} className="inline-flex items-center gap-1 text-sm font-medium text-emerald-600 hover:underline dark:text-emerald-400"><ReceiptText className="size-3.5" />{row.original.factura_display}</a>
        : row.original.estado !== 'anulada'
          ? <Badge variant="outline" className="text-amber-700 dark:text-amber-400">Sin facturar</Badge>
          : <span className="text-muted-foreground">—</span>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button asChild size="sm" variant="outline"><Link to={`/ventas/${row.original.id}`}><Eye />Ver</Link></Button>
          <Button asChild size="sm" variant="outline"><a href={`/ventas/${row.original.id}/ticket`} target="_blank" rel="noreferrer"><Printer />Ticket</a></Button>
          {row.original.pagos.length > 0 && (
            <Button asChild size="sm" variant="outline"><a href={`/ventas/${row.original.id}/recibo`} target="_blank" rel="noreferrer"><FileCheck />Recibo</a></Button>
          )}
          {user?.role === 'admin' && row.original.estado !== 'anulada' && (
            <Button size="sm" variant="outline" onClick={() => anular(row.original)}><Ban />Anular</Button>
          )}
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [user])

  const emptyMessage = tab === 'sin_facturar'
    ? 'No hay ventas pendientes de facturar.'
    : tab === 'facturadas'
      ? 'No hay ventas facturadas aún.'
      : 'No hay ventas registradas aún.'

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><ShoppingCart className="size-5 text-primary" />Ventas</h2>
        <Button asChild><Link to="/ventas/nueva"><Plus />Nueva venta</Link></Button>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="todas"><ListChecks />Todas</TabsTrigger>
          <TabsTrigger value="sin_facturar"><ReceiptText />Sin facturar</TabsTrigger>
          <TabsTrigger value="facturadas"><FileCheck />Facturadas</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-2 py-3">
          <div className="grid gap-1.5"><Label>Desde</Label><Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="w-40" /></div>
          <div className="grid gap-1.5"><Label>Hasta</Label><Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="w-40" /></div>
          <div className="grid gap-1.5">
            <Label>Buscar</Label>
            <Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()} className="min-w-48" placeholder="Buscar…" />
          </div>
          <Button size="sm" variant="outline" onClick={load}>Filtrar</Button>
          {(q || desde || hasta) && <Button size="sm" variant="outline" onClick={limpiarFiltros}>Limpiar</Button>}
        </CardContent>
      </Card>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={ventas} emptyMessage={emptyMessage} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
