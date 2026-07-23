import { useEffect, useState } from 'react'
import { api, ApiError, type ReportesData } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

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

export function Reportes() {
  const [desde, setDesde] = useState(firstOfMonthIso())
  const [hasta, setHasta] = useState(todayIso())
  const [agrupacion, setAgrupacion] = useState('dia')
  const [data, setData] = useState<ReportesData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desde, hasta, agrupacion])

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
            <Card><CardHeader><CardDescription>Ventas</CardDescription><CardTitle className="text-2xl">{formatCurrency(data.resumen.ventas_total)}</CardTitle><CardDescription>{data.resumen.ventas_cantidad} operaciones</CardDescription></CardHeader></Card>
            <Card><CardHeader><CardDescription>Facturas emitidas</CardDescription><CardTitle className="text-2xl">{data.resumen.facturas_cantidad}</CardTitle></CardHeader></Card>
            <Card><CardHeader><CardDescription>Saldo de caja del período</CardDescription><CardTitle className="text-2xl">{formatCurrency(data.resumen.caja_saldo)}</CardTitle></CardHeader></Card>
            <Card>
              <CardHeader>
                <CardDescription>Exportar</CardDescription>
                <div className="flex flex-wrap gap-2 pt-1">
                  <Button asChild size="sm" variant="outline"><a href={`/reportes/export/ventas?desde=${desde}&hasta=${hasta}&agrupacion=${agrupacion}`}>Ventas</a></Button>
                  <Button asChild size="sm" variant="outline"><a href={`/reportes/export/medios?desde=${desde}&hasta=${hasta}`}>Medios</a></Button>
                  <Button asChild size="sm" variant="outline"><a href={`/reportes/export/productos?desde=${desde}&hasta=${hasta}`}>Productos</a></Button>
                </div>
              </CardHeader>
            </Card>
          </div>

          {data.stock_bajo.length > 0 && (
            <Card>
              <CardHeader><CardTitle className="text-base text-destructive">Stock bajo</CardTitle></CardHeader>
              <CardContent>
                <ul className="flex flex-wrap gap-2">
                  {data.stock_bajo.map((s) => (
                    <li key={s.id}><Badge variant="destructive">{s.nombre}: {s.stock_actual} / mín. {s.stock_minimo}</Badge></li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">Ventas por período</CardTitle></CardHeader>
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
              <CardHeader><CardTitle className="text-base">Medios de pago</CardTitle></CardHeader>
              <CardContent>
                {data.medios.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">Sin datos.</p>
                ) : (
                  <ul className="divide-y">
                    {data.medios.map((m) => (
                      <li key={m.medio} className="flex items-center justify-between py-2 text-sm">
                        <span>{MEDIO_LABELS[m.medio] ?? m.medio} ({m.operaciones})</span>
                        <span className="font-medium">{formatCurrency(m.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-base">Productos más vendidos</CardTitle></CardHeader>
              <CardContent>
                {data.productos.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">Sin datos.</p>
                ) : (
                  <ul className="divide-y">
                    {data.productos.map((p) => (
                      <li key={p.nombre} className="flex items-center justify-between py-2 text-sm">
                        <span>{p.nombre} ({p.cantidad})</span>
                        <span className="font-medium">{formatCurrency(p.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-base">Caja por tipo</CardTitle></CardHeader>
              <CardContent>
                {data.caja.length === 0 ? (
                  <p className="py-4 text-center text-sm text-muted-foreground">Sin movimientos.</p>
                ) : (
                  <ul className="divide-y">
                    {data.caja.map((c) => (
                      <li key={c.tipo} className="flex items-center justify-between py-2 text-sm">
                        <span className="capitalize">{c.tipo} ({c.cantidad})</span>
                        <span className="font-medium">{formatCurrency(c.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
