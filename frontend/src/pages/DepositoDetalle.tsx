import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, ApiError, type Deposito, type StockItem } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, ArrowLeftRight, Building2, Pencil } from 'lucide-react'

function estadoStock(s: StockItem): { label: string; className: string } {
  if (s.stock_actual <= 0) return { label: 'Sin stock', className: 'border-destructive/30 bg-destructive/10 text-destructive' }
  if (s.stock_minimo > 0 && s.stock_actual < s.stock_minimo) return { label: 'Bajo mínimo', className: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400' }
  return { label: 'OK', className: 'border-emerald-600/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' }
}

export function DepositoDetalle() {
  const { id } = useParams<{ id: string }>()
  const depositoId = Number(id)

  const [deposito, setDeposito] = useState<Deposito | null>(null)
  const [stock, setStock] = useState<StockItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [depositoId])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function cargar() {
    setLoading(true)
    setError(null)
    try {
      const [all, s] = await Promise.all([
        api.get<Deposito[]>('/api/depositos'),
        api.get<StockItem[]>(`/api/depositos/${depositoId}/stock`),
      ])
      const d = all.find((x) => x.id === depositoId)
      if (!d) { setError('Depósito no encontrado.'); return }
      setDeposito(d)
      setStock(s)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Building2 className="size-5 text-primary" />
          {deposito ? deposito.nombre : 'Depósito'}
          {deposito?.es_default ? <Badge variant="default">Por defecto</Badge> : null}
        </h2>
        {deposito && (
          <div className="flex flex-wrap gap-2">
            <Button asChild size="sm" variant="outline"><Link to="/depositos/transferencia"><ArrowLeftRight />Transferir</Link></Button>
            <Button asChild size="sm" variant="outline"><Link to={`/depositos/${deposito.id}/editar`}><Pencil />Editar</Link></Button>
            <Button asChild size="sm" variant="outline"><Link to="/depositos"><ArrowLeft />Volver</Link></Button>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading || !deposito ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <>
          {deposito.descripcion && <p className="text-sm text-muted-foreground">{deposito.descripcion}</p>}

          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">Stock en este depósito</CardTitle>
              <span className="text-sm font-normal text-muted-foreground">{stock.length} productos</span>
            </CardHeader>
            <CardContent className="p-0">
              {stock.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">Este depósito no tiene stock registrado.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="border-b text-muted-foreground">
                    <tr>
                      <th className="p-3 text-left font-medium">Código</th>
                      <th className="p-3 text-left font-medium">Producto</th>
                      <th className="p-3 text-left font-medium">Categoría</th>
                      <th className="p-3 text-center font-medium">Unidad</th>
                      <th className="p-3 text-right font-medium">Stock actual</th>
                      <th className="p-3 text-right font-medium">Stock mínimo</th>
                      <th className="p-3 text-center font-medium">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stock.map((s) => {
                      const estado = estadoStock(s)
                      return (
                        <tr key={s.id} className="border-b last:border-0">
                          <td className="p-3 text-muted-foreground">{s.codigo || '—'}</td>
                          <td className="p-3 font-medium">{s.nombre}</td>
                          <td className="p-3 text-muted-foreground">{s.categoria || '—'}</td>
                          <td className="p-3 text-center">{s.unidad}</td>
                          <td className="p-3 text-right font-semibold">{s.stock_actual}</td>
                          <td className="p-3 text-right text-muted-foreground">{s.stock_minimo}</td>
                          <td className="p-3 text-center"><Badge variant="outline" className={estado.className}>{estado.label}</Badge></td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
