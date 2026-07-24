import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type Egreso, type Proveedor } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { DataTable, sortableHeader } from '@/components/data-table'
import { Truck, Pencil, ArrowLeft, Plus, Inbox, Trash2 } from 'lucide-react'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

const estadoVariant: Record<Egreso['estado'], 'default' | 'secondary' | 'outline'> = {
  pagado: 'default', parcial: 'default', pendiente: 'secondary',
}
const estadoBadgeClass: Record<Egreso['estado'], string> = {
  pagado: 'bg-emerald-600 text-white [a&]:hover:bg-emerald-600/90 dark:bg-emerald-500',
  parcial: 'bg-amber-500 text-white [a&]:hover:bg-amber-500/90 dark:bg-amber-600',
  pendiente: '',
}
const estadoLabel: Record<Egreso['estado'], string> = {
  pagado: 'Pagado', parcial: 'Parcial', pendiente: 'Pendiente',
}

// Restaurado desde web/templates/proveedores/detail.html. No existe un GET
// /api/proveedores/{id} en el backend (ver web/api/proveedores.py) -- se
// trae la lista completa y se busca el id. Los egresos asociados usan el
// filtro proveedor_id que sí existe en GET /api/egresos (ver
// web/api/egresos.py); ese endpoint usa el mes actual como rango por
// defecto, así que acá se pide un rango amplio explícito para traer el
// historial completo, igual que mostraba la página vieja.
export function ProveedorDetalle() {
  const { id } = useParams<{ id: string }>()
  const proveedorId = Number(id)
  const navigate = useNavigate()

  const [proveedor, setProveedor] = useState<Proveedor | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [egresos, setEgresos] = useState<Egreso[]>([])
  const [egresosLoading, setEgresosLoading] = useState(true)

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proveedorId])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function cargar() {
    setLoading(true)
    setError(null)
    try {
      const proveedores = await api.get<Proveedor[]>('/api/proveedores')
      const encontrado = proveedores.find((p) => p.id === proveedorId)
      if (!encontrado) {
        setError('Proveedor no encontrado')
        return
      }
      setProveedor(encontrado)
      cargarEgresos()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function cargarEgresos() {
    setEgresosLoading(true)
    try {
      const hoy = new Date().toISOString().slice(0, 10)
      const data = await api.get<{ items: Egreso[] }>(
        `/api/egresos?proveedor_id=${proveedorId}&desde=2000-01-01&hasta=${hoy}`,
      )
      setEgresos(data.items)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setEgresosLoading(false)
    }
  }

  async function eliminar() {
    if (!window.confirm('¿Eliminar este proveedor? Solo es posible si no tiene egresos asociados.')) return
    setError(null)
    try {
      await api.del(`/api/proveedores/${proveedorId}`)
      navigate('/proveedores')
    } catch (err) {
      setError(describeError(err))
    }
  }

  const egresoColumns = useMemo<ColumnDef<Egreso>[]>(() => [
    { accessorKey: 'fecha', header: sortableHeader('Fecha') },
    { accessorKey: 'concepto', header: 'Concepto', cell: ({ row }) => <span className="font-medium">{row.original.concepto}</span> },
    { accessorKey: 'categoria', header: 'Categoría', cell: ({ row }) => row.original.categoria || '—' },
    {
      accessorKey: 'estado',
      header: 'Estado',
      cell: ({ row }) => (
        <Badge variant={estadoVariant[row.original.estado]} className={estadoBadgeClass[row.original.estado]}>
          {estadoLabel[row.original.estado]}
        </Badge>
      ),
    },
    { accessorKey: 'total', header: 'Total', cell: ({ row }) => <span className="font-medium text-destructive">{formatCurrency(row.original.total)}</span> },
  ], [])

  const totalEgresos = egresos.reduce((sum, e) => sum + e.total, 0)

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Truck className="size-5 text-primary" />
          {proveedor ? proveedor.nombre : 'Proveedor'}
        </h2>
        <div className="flex flex-wrap gap-2">
          {proveedor && (
            <Button asChild size="sm" variant="outline"><Link to={`/proveedores/${proveedor.id}/editar`}><Pencil />Editar</Link></Button>
          )}
          <Button asChild size="sm" variant="outline"><Link to="/proveedores"><ArrowLeft />Volver</Link></Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : proveedor && (
        <>
          <Card>
            <CardHeader><CardTitle className="text-base">Datos del proveedor</CardTitle></CardHeader>
            <CardContent className="grid gap-1.5 text-sm">
              {proveedor.cuit_dni && <p><span className="text-muted-foreground">CUIT / DNI:</span> <span className="font-mono">{proveedor.cuit_dni}</span></p>}
              {proveedor.iva_condition && <p><span className="text-muted-foreground">Condición IVA:</span> {proveedor.iva_condition}</p>}
              {proveedor.address && <p><span className="text-muted-foreground">Domicilio:</span> {proveedor.address}</p>}
              {proveedor.email && <p><span className="text-muted-foreground">Email:</span> <a className="underline" href={`mailto:${proveedor.email}`}>{proveedor.email}</a></p>}
              {proveedor.phone && <p><span className="text-muted-foreground">Teléfono:</span> {proveedor.phone}</p>}
              {!proveedor.cuit_dni && !proveedor.iva_condition && !proveedor.address && !proveedor.email && !proveedor.phone && (
                <p className="text-muted-foreground">Sin datos adicionales cargados.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between space-y-0">
              <CardTitle className="text-base">Egresos registrados</CardTitle>
              <div className="flex items-center gap-3">
                {egresos.length > 0 && (
                  <span className="text-sm text-muted-foreground">Total: <span className="font-semibold text-destructive">{formatCurrency(totalEgresos)}</span></span>
                )}
                <Button asChild size="sm" variant="outline"><Link to="/egresos"><Plus />Nuevo egreso</Link></Button>
              </div>
            </CardHeader>
            <CardContent>
              {egresosLoading ? (
                <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
              ) : egresos.length === 0 ? (
                <p className="flex flex-col items-center gap-2 py-6 text-center text-sm text-muted-foreground">
                  <Inbox className="size-6" />No hay egresos registrados para este proveedor.
                </p>
              ) : (
                <DataTable columns={egresoColumns} data={egresos} emptyMessage="Sin egresos." />
              )}
            </CardContent>
          </Card>

          {/* "Eliminar proveedor" -- en la página vieja vivía al pie del
              detalle, no en la fila de la lista. */}
          <div className="flex justify-end">
            <Button variant="outline" className="text-destructive hover:text-destructive" onClick={eliminar}>
              <Trash2 />Eliminar proveedor
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
