import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type ListaPrecio } from '../api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { DataTable, sortableHeader } from '@/components/data-table'
import { Tag, Plus, Pencil, Trash2, Ban, Undo2 } from 'lucide-react'

// Lista + edición de precios ahora viven en páginas propias, igual que el
// sistema Jinja2 viejo (web/templates/listas_precio/list.html enlazaba a
// /listas-precio/{id} con "Editar precios"). Esta página queda solo como
// listado.
export function ListasPrecio() {
  const [listas, setListas] = useState<ListaPrecio[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadListas()
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function loadListas() {
    setLoading(true)
    setError(null)
    try {
      setListas(await api.get<ListaPrecio[]>('/api/listas-precio'))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function toggleActiva(lista: ListaPrecio) {
    setError(null)
    try {
      await api.put(`/api/listas-precio/${lista.id}`, {
        nombre: lista.nombre, descripcion: lista.descripcion ?? '', activa: !lista.activa,
      })
      await loadListas()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function eliminar(lista: ListaPrecio) {
    if (!window.confirm('¿Eliminar esta lista y todos sus precios?')) return
    setError(null)
    try {
      await api.del(`/api/listas-precio/${lista.id}`)
      await loadListas()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const columns = useMemo<ColumnDef<ListaPrecio>[]>(() => [
    { accessorKey: 'nombre', header: sortableHeader('Nombre'), cell: ({ row }) => (
      <span className="font-medium">
        {row.original.nombre}
        {row.original.es_default ? <Badge variant="secondary" className="ml-2">Por defecto</Badge> : null}
      </span>
    ) },
    { accessorKey: 'descripcion', header: 'Descripción', cell: ({ row }) => row.original.descripcion || '—' },
    {
      accessorKey: 'activa',
      header: 'Estado',
      cell: ({ row }) => (
        <Badge variant={row.original.activa ? 'default' : 'outline'}>
          {row.original.activa ? 'Activa' : 'Inactiva'}
        </Badge>
      ),
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button asChild size="sm" variant="outline">
            <Link to={`/listas-precio/${row.original.id}`}><Pencil />Editar precios</Link>
          </Button>
          <Button size="sm" variant="outline" onClick={() => toggleActiva(row.original)}>
            {row.original.activa ? <><Ban />Desactivar</> : <><Undo2 />Activar</>}
          </Button>
          <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}><Trash2 />Eliminar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Tag className="size-5 text-primary" />Listas de precios</h2>
        <Button asChild><Link to="/listas-precio/nueva"><Plus />Nueva lista</Link></Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable
              columns={columns}
              data={listas}
              emptyMessage={
                <div className="flex flex-col items-center gap-3 py-4">
                  <Tag className="size-10 text-muted-foreground/40" />
                  <span>No hay listas de precios creadas aún.</span>
                  <Button asChild size="sm"><Link to="/listas-precio/nueva"><Plus />Crear primera lista</Link></Button>
                </div>
              }
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
