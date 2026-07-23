import { useEffect, useState } from 'react'
import { api, ApiError, type LibrosIvaData } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

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

const EXPORTS = [
  { path: '/libros-iva/export/ventas-cbte', label: 'Ventas — comprobantes' },
  { path: '/libros-iva/export/ventas-alicuotas', label: 'Ventas — alícuotas' },
  { path: '/libros-iva/export/compras-cbte', label: 'Compras — comprobantes' },
  { path: '/libros-iva/export/compras-alicuotas', label: 'Compras — alícuotas' },
]

export function LibrosIva() {
  const [desde, setDesde] = useState(firstOfMonthIso())
  const [hasta, setHasta] = useState(todayIso())
  const [data, setData] = useState<LibrosIvaData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desde, hasta])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setData(await api.get<LibrosIvaData>(`/api/libros-iva?desde=${desde}&hasta=${hasta}`))
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Error de conexión.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">Libros IVA</h2>
        <div className="flex items-end gap-3">
          <div className="grid gap-1.5"><Label>Desde</Label><Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="w-40" /></div>
          <div className="grid gap-1.5"><Label>Hasta</Label><Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="w-40" /></div>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader><CardTitle className="text-base">Exportar REGINFO</CardTitle><CardDescription>Archivos para los aplicativos de ARCA.</CardDescription></CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {EXPORTS.map((e) => (
            <Button key={e.path} asChild size="sm" variant="outline">
              <a href={`${e.path}?desde=${desde}&hasta=${hasta}`}>{e.label}</a>
            </Button>
          ))}
        </CardContent>
      </Card>

      {loading || !data ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">Ventas</CardTitle></CardHeader>
              <CardContent className="grid gap-1 text-sm">
                <p>Comprobantes: <span className="font-medium">{data.resumen_v.cbtes}</span></p>
                <p>Neto gravado: <span className="font-medium">{formatCurrency(data.resumen_v.neto)}</span></p>
                <p>IVA: <span className="font-medium">{formatCurrency(data.resumen_v.iva)}</span></p>
                <p>Total: <span className="font-medium">{formatCurrency(data.resumen_v.total)}</span></p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-base">Compras</CardTitle></CardHeader>
              <CardContent className="grid gap-1 text-sm">
                <p>Comprobantes: <span className="font-medium">{data.resumen_c.cbtes}</span></p>
                <p>Neto gravado: <span className="font-medium">{formatCurrency(data.resumen_c.neto)}</span></p>
                <p>IVA: <span className="font-medium">{formatCurrency(data.resumen_c.iva)}</span></p>
                <p>Total: <span className="font-medium">{formatCurrency(data.resumen_c.total)}</span></p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle className="text-base">Facturas del período ({data.facturas.length})</CardTitle></CardHeader>
            <CardContent>
              {data.facturas.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Sin facturas en el período.</p>
              ) : (
                <ul className="divide-y">
                  {data.facturas.map((f) => (
                    <li key={f.id} className="flex items-center justify-between py-2 text-sm">
                      <span>{f.fecha} — {f.cliente_razon}</span>
                      <span className="font-medium">{formatCurrency(f.total)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Egresos del período ({data.egresos.length})</CardTitle></CardHeader>
            <CardContent>
              {data.egresos.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Sin egresos en el período.</p>
              ) : (
                <ul className="divide-y">
                  {data.egresos.map((e) => (
                    <li key={e.id} className="flex items-center justify-between py-2 text-sm">
                      <span>{e.fecha} — {e.proveedor_nombre || 'Sin proveedor'}</span>
                      <span className="font-medium">{formatCurrency(e.total)}</span>
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
