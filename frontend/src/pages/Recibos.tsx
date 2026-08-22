import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, ORIGEN_RECIBO_LABELS, type Recibo,
} from '../api'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { BadgeEstado } from 'libra-ui/badge-estado'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogClose,
} from '@/components/ui/dialog'
import { anchoColumnaAcciones, DataTable, sortableHeader } from 'libra-ui/data-table'
import {
  Ban, BookOpen, FileDown, ReceiptText, Search, ShoppingCart, X,
} from 'lucide-react'
import { TituloPantalla } from 'libra-ui/titulo-pantalla'

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

// El listado de recibos emitidos: sirve para reimprimir el papel que el
// cliente perdió y para anular el que salió mal. La emisión NO vive acá —
// nace donde nace el cobro (cuenta corriente, factura, venta).
export function Recibos() {
  const { user } = useAuth()

  const [desde, setDesde] = useState(firstOfMonthIso())
  const [hasta, setHasta] = useState(todayIso())
  const [q, setQ] = useState('')
  const [incluirAnulados, setIncluirAnulados] = useState(true)
  const [page, setPage] = useState(1)

  const [recibos, setRecibos] = useState<Recibo[]>([])
  const [total, setTotal] = useState(0)
  const [pageSize, setPageSize] = useState(50)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [anularTarget, setAnularTarget] = useState<Recibo | null>(null)
  const [motivo, setMotivo] = useState('')
  const [anulando, setAnulando] = useState(false)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desde, hasta, q, incluirAnulados, page])

  // Cualquier cambio de filtro vuelve a la página 1: quedarse en la 3 tras
  // filtrar muestra una tabla vacía que parece "no hay recibos".
  useEffect(() => {
    setPage(1)
  }, [desde, hasta, q, incluirAnulados])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ desde, hasta, page: String(page) })
      if (q) params.set('q', q)
      if (!incluirAnulados) params.set('incluir_anulados', 'false')
      const data = await api.get<{ recibos: Recibo[]; total: number; page_size: number }>(
        `/api/recibos?${params.toString()}`,
      )
      setRecibos(data.recibos)
      setTotal(data.total)
      setPageSize(data.page_size)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function limpiarFiltros() {
    setQ('')
    setIncluirAnulados(true)
  }

  async function anular() {
    if (!anularTarget) return
    setAnulando(true)
    setError(null)
    try {
      await api.post(`/api/recibos/${anularTarget.id}/anular`, { motivo })
      setAnularTarget(null)
      setMotivo('')
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setAnulando(false)
    }
  }

  const columns = useMemo<ColumnDef<Recibo>[]>(() => [
    {
      accessorKey: 'numero_visible',
      header: sortableHeader('N° Recibo'),
      cell: ({ row }) => (
        <span className={`font-mono text-sm ${row.original.anulado ? 'text-muted-foreground line-through' : 'font-medium'}`}>
          {row.original.numero_visible}
        </span>
      ),
    },
    { accessorKey: 'fecha', header: sortableHeader('Fecha') },
    {
      accessorKey: 'cliente_razon',
      header: 'Cliente',
      cell: ({ row }) => (
        row.original.cliente_id ? (
          <Link to={`/cuenta-corriente/${row.original.cliente_id}`} className="flex items-center gap-1 font-medium text-primary hover:underline">
            <BookOpen className="size-3.5" />{row.original.cliente_razon}
          </Link>
        ) : (
          <span>{row.original.cliente_razon}</span>
        )
      ),
    },
    {
      accessorKey: 'origen_tipo',
      header: 'Origen',
      cell: ({ row }) => {
        const label = ORIGEN_RECIBO_LABELS[row.original.origen_tipo] ?? row.original.origen_tipo
        // El origen linkea a donde nació el cobro, salvo el pago a cuenta:
        // un `cc_pago` no tiene pantalla propia, se ve en la cuenta del
        // cliente, que ya es el link de la columna Cliente.
        if (row.original.origen_tipo === 'factura' && row.original.origen_id) {
          return <Link to={`/facturas/${row.original.origen_id}`} className="flex items-center gap-1 text-primary hover:underline"><ReceiptText className="size-3.5" />{label}</Link>
        }
        if (row.original.origen_tipo === 'venta' && row.original.origen_id) {
          return <Link to={`/ventas/${row.original.origen_id}`} className="flex items-center gap-1 text-primary hover:underline"><ShoppingCart className="size-3.5" />{label}</Link>
        }
        return <Badge variant="outline">{label}</Badge>
      },
    },
    {
      accessorKey: 'concepto',
      header: 'Concepto',
      cell: ({ row }) => <span className="text-sm text-muted-foreground">{row.original.concepto || '—'}</span>,
    },
    {
      accessorKey: 'total',
      header: () => <div className="text-right">Monto</div>,
      cell: ({ row }) => (
        <div className={`text-right font-semibold ${row.original.anulado ? 'text-muted-foreground line-through' : ''}`}>
          {formatCurrency(row.original.total)}
        </div>
      ),
    },
    {
      id: 'estado',
      header: 'Estado',
      cell: ({ row }) => (
        row.original.anulado ? (
          <BadgeEstado tono="negativo" title={row.original.anulado_motivo || undefined}><Ban />Anulado</BadgeEstado>
        ) : (
          <BadgeEstado tono="ok">Vigente</BadgeEstado>
        )
      ),
    },
    {
      id: 'actions',
      header: '',
      size: anchoColumnaAcciones(2),
      minSize: anchoColumnaAcciones(2),
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          {/* El anulado también se puede imprimir: el número está consumido y
              alguien puede necesitar ver cuál era. El PDF sale con la franja. */}
          <Button asChild size="icon" variant="ghost" title="Ver PDF" aria-label="Ver PDF">
            <a href={`/api/recibos/${row.original.id}/pdf`} target="_blank" rel="noreferrer"><FileDown /></a>
          </Button>
          {user?.role === 'admin' && !row.original.anulado && (
            <Button size="icon" variant="ghost" title="Anular recibo" aria-label="Anular recibo" onClick={() => { setAnularTarget(row.original); setMotivo('') }}><Ban /></Button>
          )}
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [user])

  const totalPaginas = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <TituloPantalla icono={ReceiptText}>Recibos
          {!loading && <Badge variant="secondary">{total}</Badge>}</TituloPantalla>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-end gap-3 pt-6">
          <div className="grid gap-1.5"><Label>Desde</Label><Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="w-auto" /></div>
          <div className="grid gap-1.5"><Label>Hasta</Label><Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="w-auto" /></div>
          <div className="grid gap-1.5">
            <Label>Buscar</Label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="N°, cliente, CUIT o concepto" className="pl-8" />
            </div>
          </div>
          <label className="flex items-center gap-2 pb-2 text-sm">
            <input type="checkbox" checked={incluirAnulados} onChange={(e) => setIncluirAnulados(e.target.checked)} />
            Incluir anulados
          </label>
          <Button variant="outline" size="sm" onClick={limpiarFiltros}><X />Limpiar</Button>
        </CardContent>
      </Card>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <>
              <DataTable
                columns={columns}
                data={recibos}
                emptyMessage="No hay recibos emitidos en este período. Se emiten al cobrar: en la cuenta corriente del cliente, en una factura o en una venta."
              />
              {totalPaginas > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <span className="text-sm text-muted-foreground">Página {page} de {totalPaginas}</span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</Button>
                    <Button variant="outline" size="sm" disabled={page >= totalPaginas} onClick={() => setPage((p) => p + 1)}>Siguiente</Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={anularTarget !== null} onOpenChange={(o) => !o && setAnularTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Ban className="size-4" />Anular recibo {anularTarget?.numero_visible}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3">
            <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm dark:border-amber-900 dark:bg-amber-950/40">
              Anular <strong>no revierte el cobro</strong>: el recibo es el comprobante,
              no la plata. El número queda consumido y el papel se puede seguir
              imprimiendo, con la franja de anulado.
            </p>
            <div className="grid gap-1.5">
              <Label>Motivo <span className="font-normal text-muted-foreground">(opcional)</span></Label>
              <Input value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Se imprimió mal, se cargó dos veces…" />
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Cancelar</Button></DialogClose>
            <Button variant="destructive" disabled={anulando} onClick={anular}><Ban />{anulando ? 'Anulando…' : 'Anular recibo'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
