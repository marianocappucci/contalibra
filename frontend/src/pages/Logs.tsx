import { useEffect, useState } from 'react'
import { api, ApiError, type LogsData } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

export function Logs() {
  const [data, setData] = useState<LogsData | null>(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setData(await api.get<LogsData>(`/api/logs?page=${page}`))
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Error de conexión.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Logs de actividad</h2>
        <Button asChild size="sm" variant="outline"><a href="/admin/logs/export">Exportar CSV</a></Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading || !data ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <>
          <Card>
            <CardHeader><CardTitle className="text-base">Actividad ({data.total})</CardTitle></CardHeader>
            <CardContent className="grid gap-3">
              {data.actividad.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Sin actividad registrada.</p>
              ) : (
                <ul className="divide-y">
                  {data.actividad.map((a, i) => (
                    <li key={i} className="flex items-center justify-between py-2 text-sm">
                      <div className="flex items-center gap-2">
                        <Badge style={{ backgroundColor: data.tipo_meta[a.tipo]?.color }} className="text-white">
                          {data.tipo_meta[a.tipo]?.label ?? a.tipo}
                        </Badge>
                        <span>{a.descripcion}</span>
                      </div>
                      <div className="flex items-center gap-3 text-muted-foreground">
                        <span>{a.usuario || '—'}</span>
                        <span>{a.fecha}</span>
                        <span className="font-medium text-foreground">{formatCurrency(a.monto)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {data.total_pages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-2">
                  <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</Button>
                  <span className="text-sm text-muted-foreground">Página {data.page} de {data.total_pages}</span>
                  <Button size="sm" variant="outline" disabled={page >= data.total_pages} onClick={() => setPage((p) => p + 1)}>Siguiente</Button>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Log de autenticación</CardTitle></CardHeader>
            <CardContent>
              {data.auth_log.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Sin eventos registrados.</p>
              ) : (
                <ul className="divide-y">
                  {data.auth_log.map((e) => (
                    <li key={e.id} className="flex items-center justify-between py-2 text-sm">
                      <span className="capitalize">{e.evento} — {e.username}</span>
                      <span className="text-muted-foreground">{e.ip} · {e.ts}</span>
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
