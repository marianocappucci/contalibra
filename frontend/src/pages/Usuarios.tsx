import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type Usuario } from '../api'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { DataTable, sortableHeader } from '@/components/data-table'
import { Pencil, Plus, Trash2, Users } from 'lucide-react'

// Alta y edición ahora viven en página propia (UsuarioForm.tsx), igual que
// web/templates/usuarios/list.html enlazaba a /usuarios/nuevo y
// /usuarios/{id}/editar. Eliminar sigue siendo una acción inline (el
// template viejo tampoco tenía una página de detalle para usuarios).
export function Usuarios() {
  const { user: me } = useAuth()
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
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
      setUsuarios(await api.get<Usuario[]>('/api/usuarios'))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function eliminar(usuario: Usuario) {
    if (!window.confirm(`¿Eliminar usuario ${usuario.username}?`)) return
    setError(null)
    try {
      await api.del(`/api/usuarios/${usuario.id}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const roleLabel: Record<string, string> = { admin: 'Admin', operador: 'Operador', cajero: 'Cajero' }

  const columns = useMemo<ColumnDef<Usuario>[]>(() => [
    { accessorKey: 'username', header: sortableHeader('Usuario'), cell: ({ row }) => <span className="font-medium">{row.original.username}</span> },
    { accessorKey: 'nombre', header: 'Nombre' },
    { accessorKey: 'email', header: 'Email', cell: ({ row }) => row.original.email || '—' },
    {
      accessorKey: 'role',
      header: 'Rol',
      cell: ({ row }) => (
        <Badge variant={row.original.role === 'admin' ? 'default' : 'secondary'}>
          {roleLabel[row.original.role] ?? row.original.role}
        </Badge>
      ),
    },
    {
      accessorKey: 'activo',
      header: 'Estado',
      cell: ({ row }) => (
        <Badge
          variant="outline"
          className={row.original.activo
            ? 'border-emerald-600/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
            : 'border-destructive/30 bg-destructive/10 text-destructive'}
        >
          {row.original.activo ? 'Activo' : 'Inactivo'}
        </Badge>
      ),
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button asChild size="sm" variant="outline">
            <Link to={`/usuarios/${row.original.id}/editar`}><Pencil />Editar</Link>
          </Button>
          {row.original.username !== me?.username && (
            <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}><Trash2 />Eliminar</Button>
          )}
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [me])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Users className="size-5" />Usuarios</h2>
        <Button asChild><Link to="/usuarios/nuevo"><Plus />Nuevo usuario</Link></Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={usuarios} emptyMessage="Sin usuarios todavía." />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
