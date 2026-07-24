import { useEffect, useState } from 'react'
import {
  api, ApiError, type ReportesData, type CajaMediosData, type CajaMedioVals,
} from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  ShoppingCart, DollarSign, Receipt, Wallet, Download, TrendingUp, PieChart, Boxes,
  Banknote, Landmark, Smartphone, CreditCard, WalletCards, ArrowRightLeft, AlertTriangle,
  ArrowUp, ArrowDown, PiggyBank,
} from 'lucide-react'

function firstOfMonthIso(): string {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
}
function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

const MEDIO_LABELS: Record<string, string> = {
  efectivo: 'Efectivo', transferencia: 'Transferencia', mercadopago: 'Mercado Pago',
  cuenta_dni: 'Cuenta DNI', billetera: 'Billetera', cuenta_corriente: 'Cuenta Corriente', cheque: 'Cheque',
}
const MEDIO_ICONS: Record<string, typeof Banknote> = {
  efectivo: Banknote, transferencia: Landmark, mercadopago: Smartphone,
  cuenta_dni: CreditCard, billetera: WalletCards, cuenta_corriente: ArrowRightLeft, cheque: Receipt,
}

export function Reportes() {
  const [desde, setDesde] = useState(firstOfMonthIso())
  const [hasta, setHasta] = useState(todayIso())
  const [agrupacion, setAgrupacion] = useState('dia')
  const [data, setData] = useState<ReportesData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [cajaId, setCajaId] = useState('0')
  const [cajaMedios, setCajaMedios] = useState<CajaMediosData | null>(null)
  const [loadingCajas, setLoadingCajas] = useState(true)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desde, hasta, agrupacion])

  useEffect(() => {
    loadCajaMedios()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desde, hasta, cajaId])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setData(await api.get<ReportesData>(`/api/reportes?desde=${desde}&hasta=${hasta}&agrupacion=${agrupacion}`))
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Error de conexión.')
    } finally {
      setLoading(false)
    }
  }

  async function loadCajaMedios() {
    setLoadingCajas(true)
    try {
      setCajaMedios(await api.get<CajaMediosData>(`/api/reportes/caja-medios?desde=${desde}&hasta=${hasta}&caja_id=${cajaId}`))
    } catch {
      setCajaMedios(null)
    } finally {
      setLoadingCajas(false)
    }
  }

  const granTotalIng = cajaMedios?.cajas.reduce((s, c) => s + c.total_ingresos, 0) ?? 0
  const granTotalEgr = cajaMedios?.cajas.reduce((s, c) => s + c.total_egresos, 0) ?? 0

  function pct(vals: CajaMedioVals, total: number): number {
    return total ? Math.round((vals.ingresos / total) * 1000) / 10 : 0
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">Reportes</h2>
        <div className="flex items-end gap-3">
          <div className="grid gap-1.5"><Label>Desde</Label><Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="w-40" /></div>
          <div className="grid gap-1.5"><Label>Hasta</Label><Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="w-40" /></div>
          <div className="grid gap-1.5">
            <Label>Agrupar por</Label>
            <Select value={agrupacion} onValueChange={setAgrupacion}>
              <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="dia">Día</SelectItem>
                <SelectItem value="semana">Semana</SelectItem>
                <SelectItem value="mes">Mes</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading || !data ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="flex items-start justify-between gap-3">
                <div>
                  <CardDescription>Ventas en período</CardDescription>
                  <p className="text-2xl font-bold">{data.resumen.ventas_cantidad}</p>
                  <CardDescription>operaciones</CardDescription>
                </div>
                <span className="shrink-0 rounded-lg bg-primary/10 p-2 text-primary"><ShoppingCart /></span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-start justify-between gap-3">
                <div>
                  <CardDescription>Total vendido</CardDescription>
                  <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(data.resumen.ventas_total)}</p>
                </div>
                <span className="shrink-0 rounded-lg bg-emerald-500/10 p-2 text-emerald-600 dark:text-emerald-400"><DollarSign /></span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-start justify-between gap-3">
                <div>
                  <CardDescription>Facturas emitidas</CardDescription>
                  <p className="text-2xl font-bold">{data.resumen.facturas_cantidad}</p>
                </div>
                <span className="shrink-0 rounded-lg bg-violet-500/10 p-2 text-violet-600 dark:text-violet-400"><Receipt /></span>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-start justify-between gap-3">
                <div>
                  <CardDescription>Movimientos de caja</CardDescription>
                  <p className="text-2xl font-bold">{formatCurrency(data.resumen.caja_saldo)}</p>
                </div>
                <span className="shrink-0 rounded-lg bg-amber-500/10 p-2 text-amber-600 dark:text-amber-400"><Wallet /></span>
              </CardContent>
            </Card>
          </div>

          {data.stock_bajo.length > 0 && (
            <Card className="border-amber-500/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base text-amber-600 dark:text-amber-400">
                  <AlertTriangle className="size-4" />Stock bajo mínimo ({data.stock_bajo.length} producto{data.stock_bajo.length !== 1 ? 's' : ''})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead className="border-b text-muted-foreground">
                    <tr>
                      <th className="p-3 text-left font-medium">Código</th>
                      <th className="p-3 text-left font-medium">Producto</th>
                      <th className="p-3 text-right font-medium">Stock actual</th>
                      <th className="p-3 text-right font-medium">Mínimo</th>
                      <th className="p-3 text-right font-medium">Faltante</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.stock_bajo.map((p) => (
                      <tr key={p.id} className="border-b last:border-0">
                        <td className="p-3 text-muted-foreground">{p.codigo || '—'}</td>
                        <td className="p-3">{p.nombre}</td>
                        <td className="p-3 text-right font-semibold text-destructive">{p.stock_actual}</td>
                        <td className="p-3 text-right">{p.stock_minimo}</td>
                        <td className="p-3 text-right text-destructive">{p.stock_minimo - p.stock_actual}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader className="flex items-center justify-between space-y-0">
                <CardTitle className="flex items-center gap-2 text-base"><TrendingUp className="size-4 text-primary" />Ventas por período</CardTitle>
                <Button asChild size="sm" variant="outline"><a href={`/reportes/export/ventas?desde=${desde}&hasta=${hasta}&agrupacion=${agrupacion}`}><Download />CSV</a></Button>
              </CardHeader>
              <CardContent>
                {data.ventas_ts.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">Sin ventas en el período.</p>
                ) : (
                  <ul className="divide-y">
                    {data.ventas_ts.map((v) => (
                      <li key={v.periodo} className="flex items-center justify-between py-2 text-sm">
                        <span>{v.periodo} ({v.cantidad})</span>
                        <span className="font-medium">{formatCurrency(v.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex items-center justify-between space-y-0">
                <CardTitle className="flex items-center gap-2 text-base"><PieChart className="size-4 text-emerald-600 dark:text-emerald-400" />Medios de pago</CardTitle>
                <Button asChild size="sm" variant="outline"><a href={`/reportes/export/medios?desde=${desde}&hasta=${hasta}`}><Download />CSV</a></Button>
              </CardHeader>
              <CardContent>
                {data.medios.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">Sin datos en el período.</p>
                ) : (() => {
                  const totalMedios = data.medios.reduce((s, m) => s + m.total, 0)
                  return (
                    <ul className="grid gap-3">
                      {data.medios.map((m) => {
                        const Icon = MEDIO_ICONS[m.medio] ?? Banknote
                        const p = totalMedios ? Math.round((m.total / totalMedios) * 1000) / 10 : 0
                        return (
                          <li key={m.medio} className="grid gap-1 text-sm">
                            <div className="flex items-center justify-between">
                              <span className="flex items-center gap-2"><Icon className="size-4 text-muted-foreground" />{MEDIO_LABELS[m.medio] ?? m.medio}</span>
                              <span className="font-semibold">{formatCurrency(m.total)}</span>
                            </div>
                            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                              <div className="h-full rounded-full bg-emerald-500" style={{ width: `${p}%` }} />
                            </div>
                            <span className="text-xs text-muted-foreground">{m.operaciones} operaciones · {p}%</span>
                          </li>
                        )
                      })}
                    </ul>
                  )
                })()}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex items-center justify-between space-y-0">
                <CardTitle className="flex items-center gap-2 text-base"><Boxes className="size-4 text-purple-600 dark:text-purple-400" />Productos más vendidos</CardTitle>
                <Button asChild size="sm" variant="outline"><a href={`/reportes/export/productos?desde=${desde}&hasta=${hasta}`}><Download />CSV</a></Button>
              </CardHeader>
              <CardContent>
                {data.productos.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">Sin datos en el período.</p>
                ) : (
                  <ul className="divide-y">
                    {data.productos.map((p, i) => (
                      <li key={p.nombre} className="flex items-center justify-between py-2 text-sm">
                        <span><span className="mr-2 text-muted-foreground">{i + 1}.</span>{p.nombre} ({p.cantidad})</span>
                        <span className="font-medium">{formatCurrency(p.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Wallet className="size-4 text-amber-600 dark:text-amber-400" />Caja por tipo</CardTitle></CardHeader>
              <CardContent>
                {data.caja.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">Sin movimientos.</p>
                ) : (
                  <ul className="divide-y">
                    {data.caja.map((c) => (
                      <li key={c.tipo} className="flex items-center justify-between py-2 text-sm">
                        <span className="capitalize">{c.tipo} ({c.cantidad})</span>
                        <span className={`font-medium ${c.tipo === 'ingreso' ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}`}>{formatCurrency(c.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          {/* ── Caja por medio de cobro (restaurado de web/templates/reportes/caja_medios.html) ── */}
          <Card>
            <CardHeader className="flex-row flex-wrap items-center justify-between gap-3 space-y-0">
              <CardTitle className="flex items-center gap-2 text-base"><PiggyBank className="size-4 text-primary" />Caja por medio de cobro</CardTitle>
              <div className="flex flex-wrap items-end gap-2">
                {cajaMedios && cajaMedios.cajas_config.length > 1 && (
                  <Select value={cajaId} onValueChange={setCajaId}>
                    <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">Todas las cajas</SelectItem>
                      {cajaMedios.cajas_config.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
                <Button asChild size="sm" variant="outline"><a href={`/reportes/caja-medios/export?desde=${desde}&hasta=${hasta}&caja_id=${cajaId}`}><Download />CSV</a></Button>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4">
              {loadingCajas || !cajaMedios ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Cargando…</p>
              ) : cajaMedios.cajas.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">No hay movimientos de caja en el período seleccionado.</p>
              ) : (
                <>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <Card><CardHeader><CardDescription>Total ingresos</CardDescription><CardTitle className="text-xl text-emerald-600 dark:text-emerald-400">{formatCurrency(granTotalIng)}</CardTitle></CardHeader></Card>
                    <Card><CardHeader><CardDescription>Total egresos</CardDescription><CardTitle className="text-xl text-destructive">{formatCurrency(granTotalEgr)}</CardTitle></CardHeader></Card>
                    <Card><CardHeader><CardDescription>Saldo neto</CardDescription><CardTitle className={`text-xl ${granTotalIng >= granTotalEgr ? 'text-primary' : 'text-destructive'}`}>{formatCurrency(granTotalIng - granTotalEgr)}</CardTitle></CardHeader></Card>
                  </div>

                  {Object.keys(cajaMedios.totales).length > 0 && (
                    <div className="grid gap-1">
                      <p className="text-sm font-medium text-muted-foreground">Ingresos por medio de cobro — todas las cajas</p>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="border-b text-muted-foreground">
                            <tr>
                              <th className="p-3 text-left font-medium">Medio</th>
                              <th className="p-3 text-center font-medium">Ops.</th>
                              <th className="p-3 text-right font-medium">Ingresos</th>
                              <th className="p-3 text-left font-medium">%</th>
                              <th className="p-3 text-center font-medium">Ops.</th>
                              <th className="p-3 text-right font-medium">Egresos</th>
                              <th className="p-3 text-right font-medium">Saldo</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(cajaMedios.totales).map(([medio, vals]) => {
                              const Icon = MEDIO_ICONS[medio] ?? Banknote
                              const p = pct(vals, granTotalIng)
                              const saldo = vals.ingresos - vals.egresos
                              return (
                                <tr key={medio} className="border-b last:border-0">
                                  <td className="p-3"><span className="flex items-center gap-2"><Icon className="size-4 text-muted-foreground" />{cajaMedios.medio_label[medio] ?? medio}</span></td>
                                  <td className="p-3 text-center text-muted-foreground">{vals.ingresos_ops}</td>
                                  <td className="p-3 text-right font-semibold text-emerald-600 dark:text-emerald-400">{formatCurrency(vals.ingresos)}</td>
                                  <td className="p-3">
                                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${p}%` }} /></div>
                                    <span className="text-xs text-muted-foreground">{p}%</span>
                                  </td>
                                  <td className="p-3 text-center text-muted-foreground">{vals.egresos_ops || '—'}</td>
                                  <td className="p-3 text-right text-destructive">{vals.egresos > 0 ? formatCurrency(vals.egresos) : '—'}</td>
                                  <td className={`p-3 text-right font-semibold ${saldo >= 0 ? 'text-primary' : 'text-destructive'}`}>{formatCurrency(saldo)}</td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className="grid gap-4">
                    {cajaMedios.cajas.map((caja) => (
                      <div key={caja.id} className="rounded-lg border">
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b p-3">
                          <span className="flex items-center gap-2 font-semibold"><Wallet className="size-4 text-primary" />{caja.nombre}</span>
                          <div className="flex flex-wrap gap-4 text-sm">
                            <span className="flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400"><ArrowUp className="size-3.5" />{formatCurrency(caja.total_ingresos)}</span>
                            <span className="flex items-center gap-1 font-semibold text-destructive"><ArrowDown className="size-3.5" />{formatCurrency(caja.total_egresos)}</span>
                            <span className={`font-bold ${caja.saldo >= 0 ? 'text-primary' : 'text-destructive'}`}>Saldo: {formatCurrency(caja.saldo)}</span>
                          </div>
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="border-b text-xs text-muted-foreground">
                              <tr>
                                <th className="p-2 pl-3 text-left font-medium">Medio</th>
                                <th className="p-2 text-center font-medium">Op. entrada</th>
                                <th className="p-2 text-right font-medium">Ingresos</th>
                                <th className="p-2 text-center font-medium">Op. salida</th>
                                <th className="p-2 text-right font-medium">Egresos</th>
                                <th className="p-2 pr-3 text-right font-medium">Saldo</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(caja.medios).sort(([a], [b]) => a.localeCompare(b)).map(([medio, vals]) => {
                                const Icon = MEDIO_ICONS[medio] ?? Banknote
                                const saldoM = vals.ingresos - vals.egresos
                                return (
                                  <tr key={medio} className="border-b last:border-0">
                                    <td className="p-2 pl-3"><span className="flex items-center gap-2"><Icon className="size-4 text-muted-foreground" />{cajaMedios.medio_label[medio] ?? medio}</span></td>
                                    <td className="p-2 text-center text-muted-foreground">{vals.ingresos_ops || '—'}</td>
                                    <td className={`p-2 text-right ${vals.ingresos > 0 ? 'font-semibold text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'}`}>{vals.ingresos > 0 ? formatCurrency(vals.ingresos) : '—'}</td>
                                    <td className="p-2 text-center text-muted-foreground">{vals.egresos_ops || '—'}</td>
                                    <td className={`p-2 text-right ${vals.egresos > 0 ? 'text-destructive' : 'text-muted-foreground'}`}>{vals.egresos > 0 ? formatCurrency(vals.egresos) : '—'}</td>
                                    <td className={`p-2 pr-3 text-right font-semibold ${saldoM >= 0 ? 'text-primary' : 'text-destructive'}`}>{formatCurrency(saldoM)}</td>
                                  </tr>
                                )
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
