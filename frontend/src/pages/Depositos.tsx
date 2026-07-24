import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, type Deposito } from '../api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  ArrowLeftRight, Building2, Eye, Package, Pencil, Plus, Star, Trash2,
} from 'lucide-react'

export function Depositos() {
  const [depositos, setDepositos] = useState<Deposito[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    load()
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setDepositos(await api.get<Deposito[]>('/api/depositos'))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function setDefault(d: Deposito) {
    setError(null)
    try {
      await api.post(`/api/depositos/${d.id}/set-default`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function eliminar(d: Deposito) {
    if (!window.confirm(`¿Eliminar el depósito «${d.nombre}»?`)) return
    setError(null)
    try {
      await api.del(`/api/depositos/${d.id}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Building2 className="size-5" />Depósitos</h2>
        <div className="flex items-center gap-2">
          <Button asChild variant="outline"><Link to="/depositos/transferencia"><ArrowLeftRight />Transferir stock</Link></Button>
          <Button asChild><Link to="/depositos/nuevo"><Plus />Nuevo depósito</Link></Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : depositos.length === 0 ? (
        <Card><CardContent className="py-6 text-center text-sm text-muted-foreground">No hay depósitos creados.</CardContent></Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {depositos.map((d) => (
            <Card key={d.id} className={d.activo ? '' : 'opacity-50'}>
              <CardContent className="grid gap-3">
                <div>
                  <p className="flex items-center gap-2 font-semibold"><Building2 className="size-4 text-primary" />{d.nombre}</p>
                  <div className="mt-1 flex gap-1.5">
                    {d.es_default ? <Badge variant="default">Por defecto</Badge> : null}
                    {!d.activo && <Badge variant="secondary">Inactivo</Badge>}
                  </div>
                </div>
                {d.descripcion && <p className="text-sm text-muted-foreground">{d.descripcion}</p>}
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Package className="size-4" />{d.total_productos} producto{d.total_productos !== 1 ? 's' : ''} con stock
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button asChild size="sm" variant="outline"><Link to={`/depositos/${d.id}`}><Eye />Ver stock</Link></Button>
                  <Button asChild size="sm" variant="outline"><Link to={`/depositos/${d.id}/editar`}><Pencil />Editar</Link></Button>
                  {!d.es_default && (
                    <>
                      <Button size="sm" variant="outline" title="Usar como depósito por defecto" onClick={() => setDefault(d)}><Star />Predeterminar</Button>
                      <Button size="sm" variant="outline" onClick={() => eliminar(d)}><Trash2 /></Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
