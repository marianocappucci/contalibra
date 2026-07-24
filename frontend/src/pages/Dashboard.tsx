import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, type DashboardData } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import {
  Gauge, Receipt, ArrowDownCircle, ArrowUpCircle, Wallet, ClipboardList,
  Hourglass, CheckCircle2, Inbox, History,
} from 'lucide-react'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 }).format(value)
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('es-AR')
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    load()
  }, [])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setData(await api.get<DashboardData>('/api/dashboard'))
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Error de conexión.')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Gauge className="size-5 text-primary" />Dashboard</h2>
        {data && (
          <span className="text-sm text-muted-foreground">{formatDate(data.mes_hasta)}</span>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      )}

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="flex items-start justify-between gap-3">
                <div>
                  <CardDescription>Facturado este mes</CardDescription>
                  <p className="text-2xl font-bold text-primary">{formatCurrency(data.facturado_mes)}</p>
                  <CardDescription>
                    {data.cant_facturas_mes} factura{data.cant_facturas_mes !== 1 ? 's' : ''}
                  </CardDescription>
                </div>
                <span className="shrink-0 rounded-lg bg-primary/10 p-2 text-primary"><Receipt /></span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-start justify-between gap-3">
                <div>
                  <CardDescription>Cobrado este mes</CardDescription>
                  <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(data.cobrado_mes)}</p>
                  <CardDescription>Ingresos en caja</CardDescription>
                </div>
                <span className="shrink-0 rounded-lg bg-emerald-500/10 p-2 text-emerald-600 dark:text-emerald-400"><ArrowDownCircle /></span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-start justify-between gap-3">
                <div>
                  <CardDescription>Egresos este mes</CardDescription>
                  <p className="text-2xl font-bold text-destructive">{formatCurrency(data.egresos_mes)}</p>
                  <CardDescription>Gastos en caja</CardDescription>
                </div>
                <span className="shrink-0 rounded-lg bg-destructive/10 p-2 text-destructive"><ArrowUpCircle /></span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-start justify-between gap-3">
                <div>
                  <CardDescription>Saldo total en caja</CardDescription>
                  <p className={data.saldo_total >= 0 ? 'text-2xl font-bold text-emerald-600 dark:text-emerald-400' : 'text-2xl font-bold text-destructive'}>
                    {formatCurrency(data.saldo_total)}
                  </p>
                  <CardDescription>Histórico acumulado</CardDescription>
                </div>
                <span className={`shrink-0 rounded-lg p-2 ${data.saldo_total >= 0 ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-destructive/10 text-destructive'}`}><Wallet /></span>
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button asChild size="sm"><Link to="/facturas/nueva">+ Nueva Factura</Link></Button>
            <Button asChild size="sm" variant="outline"><Link to="/presupuestos/nuevo">+ Nuevo Presupuesto</Link></Button>
            <Button asChild size="sm" variant="outline"><Link to="/remitos/nuevo">+ Nuevo Remito</Link></Button>
            <Button asChild size="sm" variant="outline"><Link to="/caja?nuevo=1">+ Nuevo Movimiento de Caja</Link></Button>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader className="flex items-center justify-between space-y-0">
                <CardTitle className="flex items-center gap-2 text-base"><Hourglass className="size-4 text-amber-500" />Facturas sin cobrar</CardTitle>
                <Button asChild size="sm" variant="outline"><Link to="/facturas">Ver todas</Link></Button>
              </CardHeader>
              <CardContent>
                {data.facturas_sin_cobrar.length === 0 ? (
                  <p className="flex flex-col items-center gap-2 py-4 text-center text-sm text-muted-foreground">
                    <CheckCircle2 className="size-6 text-emerald-500" />Todas las facturas están cobradas.
                  </p>
                ) : (
                  <ul className="divide-y">
                    {data.facturas_sin_cobrar.map((f) => (
                      <li key={f.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                        <div className="min-w-0">
                          <p className="font-medium">
                            <span className="text-muted-foreground">{f.letra}</span> {f.label_numero}
                          </p>
                          <p className="truncate text-muted-foreground">{f.cliente_razon} — {formatDate(f.fecha)}</p>
                        </div>
                        <div className="flex shrink-0 items-center gap-3">
                          <span className="font-medium">{formatCurrency(f.total)}</span>
                          <Button asChild size="sm" variant="outline"><Link to={`/facturas/${f.id}`}>Ver</Link></Button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex items-center justify-between space-y-0">
                <CardTitle className="flex items-center gap-2 text-base"><ClipboardList className="size-4 text-sky-500" />Presupuestos sin respuesta</CardTitle>
                <Button asChild size="sm" variant="outline"><Link to="/presupuestos">Ver todos</Link></Button>
              </CardHeader>
              <CardContent>
                {data.presupuestos_pendientes.length === 0 ? (
                  <p className="flex flex-col items-center gap-2 py-4 text-center text-sm text-muted-foreground">
                    <Inbox className="size-6" />Sin presupuestos pendientes.
                  </p>
                ) : (
                  <ul className="divide-y">
                    {data.presupuestos_pendientes.map((p) => (
                      <li key={p.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                        <div className="min-w-0">
                          <p className="font-medium">{p.number}</p>
                          <p className="truncate text-muted-foreground">{p.client_name}</p>
                        </div>
                        <div className="flex shrink-0 items-center gap-3">
                          <span className="font-medium">{formatCurrency(p.total)}</span>
                          <Button asChild size="sm" variant="outline"><Link to={`/presupuestos/${p.id}`}>Ver</Link></Button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex items-center justify-between space-y-0">
              <CardTitle className="flex items-center gap-2 text-base"><History className="size-4" />Últimos movimientos de caja</CardTitle>
              <Button asChild size="sm" variant="outline"><Link to="/caja">Ver caja completa</Link></Button>
            </CardHeader>
            <CardContent>
              {data.ultimos_movimientos.length === 0 ? (
                <p className="flex flex-col items-center gap-2 py-4 text-center text-sm text-muted-foreground">
                  <Inbox className="size-6" />Sin movimientos registrados.
                </p>
              ) : (
                <ul className="divide-y">
                  {data.ultimos_movimientos.map((m) => (
                    <li key={m.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                      <div className="min-w-0">
                        <p className="font-medium">{m.concepto}</p>
                        <p className="truncate text-muted-foreground">{formatDate(m.fecha)}{m.referencia ? ` — ${m.referencia}` : ''}</p>
                      </div>
                      <span className={`shrink-0 font-medium ${m.tipo === 'ingreso' ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}`}>
                        {m.tipo === 'ingreso' ? '+' : '−'} {formatCurrency(m.monto)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
