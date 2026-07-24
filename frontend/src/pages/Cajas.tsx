import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, MEDIOS_PAGO_LABELS, type CajaConfig } from '../api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { SquareStack, Plus, Eye, Pencil, Trash2, Star, Wallet } from 'lucide-react'

export function Cajas() {
  const [cajas, setCajas] = useState<CajaConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { load() }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setCajas(await api.get<CajaConfig[]>('/api/cajas'))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function setDefault(c: CajaConfig) {
    setError(null)
    try {
      await api.post(`/api/cajas/${c.id}/set-default`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function eliminar(c: CajaConfig) {
    if (!window.confirm(`¿Eliminar la caja «${c.nombre}»?`)) return
    setError(null)
    try {
      await api.del(`/api/cajas/${c.id}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><SquareStack className="size-5 text-primary" />Cajas</h2>
        <Button asChild><Link to="/cajas/nueva"><Plus />Nueva caja</Link></Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : cajas.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {cajas.map((c) => (
            <Card key={c.id} className={c.activo ? undefined : 'opacity-50'}>
              <CardContent className="grid gap-2 pt-6">
                <div className="flex items-start justify-between gap-2">
                  <p className="flex items-center gap-2 font-semibold"><Wallet className="size-4 text-emerald-600 dark:text-emerald-400" />{c.nombre}</p>
                  <div className="flex gap-1">
                    {!!c.es_default && <Badge className="bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-400">Por defecto</Badge>}
                    {!c.activo && <Badge variant="secondary">Inactiva</Badge>}
                  </div>
                </div>

                {c.descripcion && <p className="text-sm text-muted-foreground">{c.descripcion}</p>}

                <div>
                  <p className="mb-1 text-sm text-muted-foreground">Medios de pago:</p>
                  <div className="flex flex-wrap gap-1">
                    {c.medios_pago.length > 0 ? (
                      c.medios_pago.map((m) => <Badge key={m} variant="outline">{MEDIOS_PAGO_LABELS[m] ?? m}</Badge>)
                    ) : (
                      <span className="text-sm text-muted-foreground">Sin medios configurados</span>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 pt-1">
                  <Button size="sm" variant="outline" asChild><Link to={`/caja?caja_id=${c.id}`}><Eye />Ver movimientos</Link></Button>
                  <Button size="sm" variant="outline" asChild><Link to={`/cajas/${c.id}/editar`}><Pencil />Editar</Link></Button>
                  {!c.es_default && (
                    <>
                      <Button size="sm" variant="outline" onClick={() => setDefault(c)} title="Usar como caja por defecto"><Star />Predeterminar</Button>
                      <Button size="sm" variant="outline" onClick={() => eliminar(c)}><Trash2 /></Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card><CardContent className="py-6 text-center text-muted-foreground">No hay cajas configuradas.</CardContent></Card>
      )}
    </div>
  )
}
