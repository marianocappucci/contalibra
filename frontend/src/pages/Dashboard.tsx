import { useEffect, useState } from 'react'
import { api, ApiError, type DashboardData } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

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
        <h2 className="text-lg font-semibold">Dashboard</h2>
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
              <CardHeader>
                <CardDescription>Facturado este mes</CardDescription>
                <CardTitle className="text-2xl text-primary">{formatCurrency(data.facturado_mes)}</CardTitle>
                <CardDescription>
                  {data.cant_facturas_mes} factura{data.cant_facturas_mes !== 1 ? 's' : ''}
                </CardDescription>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Cobrado este mes</CardDescription>
                <CardTitle className="text-2xl text-emerald-600 dark:text-emerald-400">{formatCurrency(data.cobrado_mes)}</CardTitle>
                <CardDescription>Ingresos en caja</CardDescription>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Egresos este mes</CardDescription>
                <CardTitle className="text-2xl text-destructive">{formatCurrency(data.egresos_mes)}</CardTitle>
                <CardDescription>Gastos en caja</CardDescription>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardDescription>Saldo total en caja</CardDescription>
                <CardTitle className={data.saldo_total >= 0 ? 'text-2xl text-emerald-600 dark:text-emerald-400' : 'text-2xl text-destructive'}>
                  {formatCurrency(data.saldo_total)}
                </CardTitle>
                <CardDescription>Histórico acumulado</CardDescription>
              </CardHeader>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Facturas sin cobrar</CardTitle>
              </CardHeader>
              <CardContent>
                {data.facturas_sin_cobrar.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">Todas las facturas están cobradas.</p>
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
                        <span className="shrink-0 font-medium">{formatCurrency(f.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Presupuestos sin respuesta</CardTitle>
              </CardHeader>
              <CardContent>
                {data.presupuestos_pendientes.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">Sin presupuestos pendientes.</p>
                ) : (
                  <ul className="divide-y">
                    {data.presupuestos_pendientes.map((p) => (
                      <li key={p.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                        <div className="min-w-0">
                          <p className="font-medium">{p.number}</p>
                          <p className="truncate text-muted-foreground">{p.client_name}</p>
                        </div>
                        <span className="shrink-0 font-medium">{formatCurrency(p.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Últimos movimientos de caja</CardTitle>
            </CardHeader>
            <CardContent>
              {data.ultimos_movimientos.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Sin movimientos registrados.</p>
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
