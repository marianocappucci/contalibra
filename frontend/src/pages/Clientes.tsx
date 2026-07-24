import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type Cliente } from '../api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { DataTable, sortableHeader } from '@/components/data-table'
import { Users, Plus, Pencil, Eye, Trash2, Undo2 } from 'lucide-react'

export function Clientes() {
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadClientes()
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function loadClientes() {
    setLoading(true)
    setError(null)
    try {
      setClientes(await api.get<Cliente[]>('/api/clientes'))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  // El "eliminar" de web/templates/clientes/list.html en realidad desactiva
  // (existe un endpoint de "activar" para deshacerlo) -- se conserva el
  // mismo texto de confirmación y verbo que usaba la página vieja.
  async function toggleActivo(cliente: Cliente) {
    if (cliente.activo && !window.confirm(`¿Eliminar a ${cliente.name}?`)) return
    setError(null)
    try {
      const path = cliente.activo
        ? `/api/clientes/${cliente.id}/desactivar`
        : `/api/clientes/${cliente.id}/activar`
      await api.post(path)
      await loadClientes()
    } catch (err) {
      setError(describeError(err))
    }
  }

  // Orden y columnas igual a web/templates/clientes/list.html: Nombre,
  // CUIT/DNI, Condición IVA, Teléfono, acciones -- esa tabla vieja no tenía
  // columnas de Email ni de Estado separadas (el "Inactivo" viaja como
  // badge junto al nombre, igual que acá). "Ver" y "Editar" ahora navegan
  // a páginas propias (/clientes/:id y /clientes/:id/editar) en vez de
  // desplegar una ficha inline, igual que hacía el sistema Jinja2 viejo.
  const columns = useMemo<ColumnDef<Cliente>[]>(() => [
    { accessorKey: 'name', header: sortableHeader('Nombre / Razón social'), cell: ({ row }) => (
      <Link to={`/clientes/${row.original.id}`} className="font-medium hover:underline">
        {row.original.name}
        {!row.original.activo && <Badge variant="secondary" className="ml-2">Inactivo</Badge>}
      </Link>
    ) },
    { accessorKey: 'cuit_dni', header: 'CUIT / DNI', cell: ({ row }) => row.original.cuit_dni || '—' },
    { accessorKey: 'iva_condition', header: 'Condición IVA', cell: ({ row }) => row.original.iva_condition || '—' },
    { accessorKey: 'phone', header: 'Teléfono', cell: ({ row }) => row.original.phone || '—' },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button asChild size="sm" variant="outline" title="Ver ficha">
            <Link to={`/clientes/${row.original.id}`}><Eye />Ver</Link>
          </Button>
          {row.original.activo && (
            <Button asChild size="sm" variant="outline">
              <Link to={`/clientes/${row.original.id}/editar`}><Pencil />Editar</Link>
            </Button>
          )}
          {row.original.activo ? (
            <Button size="sm" variant="outline" className="text-destructive hover:text-destructive" onClick={() => toggleActivo(row.original)}><Trash2 />Eliminar</Button>
          ) : (
            <Button size="sm" variant="outline" title="Reactivar cliente" onClick={() => toggleActivo(row.original)}><Undo2 />Reactivar</Button>
          )}
        </div>
      ),
    },
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Users className="size-5 text-primary" />Clientes</h2>
        <Button asChild><Link to="/clientes/nuevo"><Plus />Nuevo cliente</Link></Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable
              columns={columns}
              data={clientes}
              emptyMessage="No hay clientes registrados aún."
              getRowClassName={(c) => !c.activo ? 'opacity-50' : undefined}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
