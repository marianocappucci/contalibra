import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type Proveedor } from '../api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTable, sortableHeader } from '@/components/data-table'
import { Truck, Plus, Pencil, Eye, Search, X } from 'lucide-react'

export function Proveedores() {
  const [proveedores, setProveedores] = useState<Proveedor[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')

  useEffect(() => {
    loadProveedores()
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function loadProveedores(query = q) {
    setLoading(true)
    setError(null)
    try {
      const path = query ? `/api/proveedores?q=${encodeURIComponent(query)}` : '/api/proveedores'
      setProveedores(await api.get<Proveedor[]>(path))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function limpiarBusqueda() {
    setQ('')
    loadProveedores('')
  }

  // Orden igual a web/templates/proveedores/list.html: Nombre, CUIT/DNI,
  // Email, Teléfono, acciones. Esa fila solo tenía Ver + Editar -- "Eliminar
  // proveedor" vivía como botón aparte al pie de la página de detalle
  // (proveedores/detail.html), no en la fila de la lista. "Ver" y "Editar"
  // ahora navegan a páginas propias (/proveedores/:id y
  // /proveedores/:id/editar) en vez de desplegar contenido inline, igual
  // que hacía el sistema Jinja2 viejo.
  const columns = useMemo<ColumnDef<Proveedor>[]>(() => [
    { accessorKey: 'nombre', header: sortableHeader('Nombre'), cell: ({ row }) => (
      <Link to={`/proveedores/${row.original.id}`} className="font-medium hover:underline">{row.original.nombre}</Link>
    ) },
    { accessorKey: 'cuit_dni', header: 'CUIT/DNI', cell: ({ row }) => row.original.cuit_dni || '—' },
    { accessorKey: 'email', header: 'Email', cell: ({ row }) => row.original.email || '—' },
    { accessorKey: 'phone', header: 'Teléfono', cell: ({ row }) => row.original.phone || '—' },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button asChild size="sm" variant="outline"><Link to={`/proveedores/${row.original.id}`}><Eye />Ver</Link></Button>
          <Button asChild size="sm" variant="outline"><Link to={`/proveedores/${row.original.id}/editar`}><Pencil />Editar</Link></Button>
        </div>
      ),
    },
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Truck className="size-5 text-primary" />Proveedores</h2>
        <Button asChild><Link to="/proveedores/nuevo"><Plus />Nuevo proveedor</Link></Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardContent className="flex flex-wrap items-center gap-2 py-3">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadProveedores()}
            placeholder="Buscar por nombre o CUIT…"
            className="w-72"
          />
          <Button variant="outline" size="icon" onClick={() => loadProveedores()}><Search /></Button>
          {q && <Button variant="outline" size="icon" onClick={limpiarBusqueda}><X /></Button>}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable
              columns={columns}
              data={proveedores}
              emptyMessage={q ? `No se encontraron proveedores para "${q}".` : 'No hay proveedores registrados aún.'}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
