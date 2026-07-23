import { useEffect, useMemo, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, ROLES, type Usuario } from '../api'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form'
import { DataTable, sortableHeader } from '@/components/data-table'

const crearSchema = z.object({
  username: z.string().trim().min(1, 'El usuario es obligatorio'),
  nombre: z.string().trim().min(1, 'El nombre es obligatorio'),
  email: z.string().trim().email('Email inválido').optional().or(z.literal('')),
  password: z.string().min(6, 'Mínimo 6 caracteres'),
  role: z.string(),
})
type CrearFormValues = z.infer<typeof crearSchema>
const EMPTY_CREATE: CrearFormValues = { username: '', nombre: '', email: '', password: '', role: 'operador' }

const editarSchema = z.object({
  nombre: z.string().trim().min(1, 'El nombre es obligatorio'),
  email: z.string().trim().email('Email inválido').optional().or(z.literal('')),
  role: z.string(),
  new_password: z.string().optional(),
})
type EditarFormValues = z.infer<typeof editarSchema>
const EMPTY_EDIT: EditarFormValues = { nombre: '', email: '', role: 'operador', new_password: '' }

export function Usuarios() {
  const { user: me } = useAuth()
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  const createForm = useForm<CrearFormValues>({ resolver: zodResolver(crearSchema), defaultValues: EMPTY_CREATE })
  const editForm = useForm<EditarFormValues>({ resolver: zodResolver(editarSchema), defaultValues: EMPTY_EDIT })

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

  function startEdit(usuario: Usuario) {
    setEditingId(usuario.id)
    setCreating(false)
    editForm.reset({ nombre: usuario.nombre, email: usuario.email ?? '', role: usuario.role, new_password: '' })
  }

  async function handleCreate(values: CrearFormValues) {
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/usuarios', {
        username: values.username, nombre: values.nombre, email: values.email || '',
        password: values.password, role: values.role,
      })
      setCreating(false)
      createForm.reset(EMPTY_CREATE)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleEdit(values: EditarFormValues) {
    if (editingId === null) return
    setSaving(true)
    setError(null)
    try {
      const original = usuarios.find((u) => u.id === editingId)
      await api.put(`/api/usuarios/${editingId}`, {
        nombre: values.nombre, email: values.email || '', role: values.role,
        activo: !!original?.activo, new_password: values.new_password || '',
      })
      setEditingId(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function toggleActivo(usuario: Usuario) {
    setError(null)
    try {
      await api.put(`/api/usuarios/${usuario.id}`, {
        nombre: usuario.nombre, email: usuario.email ?? '', role: usuario.role,
        activo: !usuario.activo, new_password: '',
      })
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function eliminar(usuario: Usuario) {
    setError(null)
    try {
      await api.del(`/api/usuarios/${usuario.id}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const columns = useMemo<ColumnDef<Usuario>[]>(() => [
    { accessorKey: 'username', header: sortableHeader('Usuario'), cell: ({ row }) => <span className="font-medium">{row.original.username}</span> },
    { accessorKey: 'nombre', header: 'Nombre' },
    { accessorKey: 'email', header: 'Email', cell: ({ row }) => row.original.email || '—' },
    { accessorKey: 'role', header: 'Rol', cell: ({ row }) => <span className="capitalize">{row.original.role}</span> },
    {
      accessorKey: 'activo',
      header: 'Estado',
      cell: ({ row }) => (
        <Badge variant={row.original.activo ? 'default' : 'outline'}>
          {row.original.activo ? 'Activo' : 'Inactivo'}
        </Badge>
      ),
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => startEdit(row.original)}>Editar</Button>
          <Button size="sm" variant="outline" onClick={() => toggleActivo(row.original)}>
            {row.original.activo ? 'Desactivar' : 'Activar'}
          </Button>
          {row.original.username !== me?.username && (
            <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}>Eliminar</Button>
          )}
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [usuarios, me])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Usuarios</h2>
        {!creating && (
          <Button onClick={() => { setCreating(true); setEditingId(null) }}>+ Nuevo usuario</Button>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {creating && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nuevo usuario</CardTitle></CardHeader>
          <CardContent>
            <Form {...createForm}>
              <form className="flex flex-wrap items-start gap-3" onSubmit={createForm.handleSubmit(handleCreate)}>
                <FormField control={createForm.control} name="username" render={({ field }) => (
                  <FormItem><FormLabel>Usuario</FormLabel><FormControl><Input {...field} className="w-40" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={createForm.control} name="nombre" render={({ field }) => (
                  <FormItem><FormLabel>Nombre</FormLabel><FormControl><Input {...field} className="w-48" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={createForm.control} name="email" render={({ field }) => (
                  <FormItem><FormLabel>Email</FormLabel><FormControl><Input type="email" {...field} className="w-52" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={createForm.control} name="password" render={({ field }) => (
                  <FormItem><FormLabel>Contraseña</FormLabel><FormControl><Input type="password" {...field} className="w-40" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={createForm.control} name="role" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Rol</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl><SelectTrigger className="w-32"><SelectValue /></SelectTrigger></FormControl>
                      <SelectContent>
                        {ROLES.map((r) => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
                <div className="flex gap-2 pt-6">
                  <Button type="submit" disabled={saving}>{saving ? 'Guardando…' : 'Crear'}</Button>
                  <Button type="button" variant="outline" onClick={() => { setCreating(false); createForm.reset(EMPTY_CREATE) }}>Cancelar</Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>
      )}

      {editingId !== null && (
        <Card>
          <CardHeader><CardTitle className="text-base">Editar usuario</CardTitle></CardHeader>
          <CardContent>
            <Form {...editForm}>
              <form className="flex flex-wrap items-start gap-3" onSubmit={editForm.handleSubmit(handleEdit)}>
                <FormField control={editForm.control} name="nombre" render={({ field }) => (
                  <FormItem><FormLabel>Nombre</FormLabel><FormControl><Input {...field} className="w-48" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={editForm.control} name="email" render={({ field }) => (
                  <FormItem><FormLabel>Email</FormLabel><FormControl><Input type="email" {...field} className="w-52" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={editForm.control} name="role" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Rol</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl><SelectTrigger className="w-32"><SelectValue /></SelectTrigger></FormControl>
                      <SelectContent>
                        {ROLES.map((r) => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={editForm.control} name="new_password" render={({ field }) => (
                  <FormItem><FormLabel>Nueva contraseña (opcional)</FormLabel><FormControl><Input type="password" {...field} className="w-40" /></FormControl><FormMessage /></FormItem>
                )} />
                <div className="flex gap-2 pt-6">
                  <Button type="submit" disabled={saving}>{saving ? 'Guardando…' : 'Guardar'}</Button>
                  <Button type="button" variant="outline" onClick={() => setEditingId(null)}>Cancelar</Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>
      )}

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
