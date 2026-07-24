import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError, type Cliente } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { IdCard, Pencil, Undo2, ArrowLeft } from 'lucide-react'

// Restaurado desde web/templates/clientes/detail.html. No existe un GET
// /api/clientes/{id} en el backend (ver web/api/clientes.py) -- se trae la
// lista completa y se busca el id, igual que hacía la ficha inline vieja de
// esta SPA antes de que esta página existiera.
//
// Las tablas de facturas/presupuestos/remitos asociados y los alias de
// facturación de Mercado Pago que tenía la página Jinja2 vieja todavía no
// tienen endpoint en la API de la SPA (ni filtro por cliente en
// GET /api/facturas, /api/presupuestos, /api/remitos, ni endpoints de
// alias-facturacion) -- ver reporte de auditoría. Queda pendiente para
// cuando se agregue esa API.
export function ClienteDetalle() {
  const { id } = useParams<{ id: string }>()
  const clienteId = Number(id)
  const navigate = useNavigate()

  const [cliente, setCliente] = useState<Cliente | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteId])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function cargar() {
    setLoading(true)
    setError(null)
    try {
      const clientes = await api.get<Cliente[]>('/api/clientes')
      const encontrado = clientes.find((c) => c.id === clienteId)
      if (!encontrado) {
        setError('Cliente no encontrado')
      } else {
        setCliente(encontrado)
      }
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function reactivar() {
    if (!cliente) return
    setError(null)
    try {
      await api.post(`/api/clientes/${cliente.id}/activar`)
      await cargar()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <IdCard className="size-5 text-primary" />
            {cliente ? cliente.name : 'Cliente'}
          </h2>
          {cliente && !cliente.activo && <Badge variant="secondary">Inactivo</Badge>}
        </div>
        <div className="flex flex-wrap gap-2">
          {cliente && cliente.activo && (
            <Button asChild size="sm" variant="outline"><Link to={`/clientes/${cliente.id}/editar`}><Pencil />Editar</Link></Button>
          )}
          {cliente && !cliente.activo && (
            <Button size="sm" variant="outline" onClick={reactivar}><Undo2 />Reactivar cliente</Button>
          )}
          <Button asChild size="sm" variant="outline"><Link to="/clientes"><ArrowLeft />Volver</Link></Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : cliente && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Datos del cliente</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-1.5 text-sm">
            <p><span className="text-muted-foreground">Nombre / Razón social:</span> <span className="font-medium">{cliente.name}</span></p>
            {cliente.cuit_dni && <p><span className="text-muted-foreground">CUIT / DNI:</span> <span className="font-mono">{cliente.cuit_dni}</span></p>}
            {cliente.iva_condition && <p><span className="text-muted-foreground">Condición IVA:</span> {cliente.iva_condition}</p>}
            {cliente.address && <p><span className="text-muted-foreground">Domicilio:</span> {cliente.address}</p>}
            {cliente.phone && <p><span className="text-muted-foreground">Teléfono:</span> {cliente.phone}</p>}
            {cliente.email && <p><span className="text-muted-foreground">Email:</span> <a className="underline" href={`mailto:${cliente.email}`}>{cliente.email}</a></p>}
            <p><span className="text-muted-foreground">Facturación automática MP:</span> {cliente.auto_facturar ? 'Activa' : 'Inactiva'}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Las facturas, presupuestos y remitos asociados a este cliente, y los alias de facturación de
              Mercado Pago, todavía no tienen un endpoint en la API de la SPA (existían en la página de
              detalle Jinja2 vieja vía <code>/clientes/&#123;id&#125;</code>) — ver reporte de auditoría.
            </p>
          </CardContent>
        </Card>
      )}

      {!loading && !cliente && !error && (
        <p className="py-6 text-center text-sm text-muted-foreground">Cliente no encontrado.</p>
      )}
      {!loading && error === 'Cliente no encontrado' && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => navigate('/clientes')}>Volver al listado</Button>
        </div>
      )}
    </div>
  )
}
