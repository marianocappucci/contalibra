import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { api, ApiError, ROLES, type Usuario } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form'
import { Check, UserCog } from 'lucide-react'

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
  activo: z.string(),
  new_password: z.string().optional(),
})
type EditarFormValues = z.infer<typeof editarSchema>
const EMPTY_EDIT: EditarFormValues = { nombre: '', email: '', role: 'operador', activo: '1', new_password: '' }

// Misma página para alta y edición, igual que web/templates/usuarios/form.html
// (que ya usaba `{{ usuario }}` para decidir modo) -- si hay :id en la ruta
// (/usuarios/:id/editar) precarga el usuario existente.
export function UsuarioForm() {
  const { id } = useParams<{ id: string }>()
  const editingId = id ? Number(id) : null
  const navigate = useNavigate()

  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [loadingUsuario, setLoadingUsuario] = useState(Boolean(editingId))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createForm = useForm<CrearFormValues>({ resolver: zodResolver(crearSchema), defaultValues: EMPTY_CREATE })
  const editForm = useForm<EditarFormValues>({ resolver: zodResolver(editarSchema), defaultValues: EMPTY_EDIT })

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  useEffect(() => {
    if (!editingId) return
    api.get<Usuario[]>('/api/usuarios').then((usuarios) => {
      const encontrado = usuarios.find((u) => u.id === editingId) ?? null
      setUsuario(encontrado)
      if (encontrado) {
        editForm.reset({
          nombre: encontrado.nombre, email: encontrado.email ?? '', role: encontrado.role,
          activo: encontrado.activo ? '1' : '0', new_password: '',
        })
      } else {
        setError('No se encontró el usuario.')
      }
    }).catch((err) => setError(describeError(err))).finally(() => setLoadingUsuario(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingId])

  async function handleCreate(values: CrearFormValues) {
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/usuarios', {
        username: values.username, nombre: values.nombre, email: values.email || '',
        password: values.password, role: values.role,
      })
      navigate('/usuarios')
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
      await api.put(`/api/usuarios/${editingId}`, {
        nombre: values.nombre, email: values.email || '', role: values.role,
        activo: values.activo === '1', new_password: values.new_password || '',
      })
      navigate('/usuarios')
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  if (editingId && (loadingUsuario || !usuario)) {
    return (
      <div className="grid gap-4">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><UserCog className="size-5" />Editar usuario</h2>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {loadingUsuario && <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>}
      </div>
    )
  }

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <UserCog className="size-5" />{editingId ? 'Editar usuario' : 'Nuevo usuario'}
      </h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader><CardTitle className="text-base">Datos del usuario</CardTitle></CardHeader>
        <CardContent>
          {editingId ? (
            <Form {...editForm}>
              <form className="grid max-w-xl gap-4" onSubmit={editForm.handleSubmit(handleEdit)}>
                <FormItem>
                  <FormLabel>Usuario</FormLabel>
                  <FormControl><Input value={usuario?.username ?? ''} readOnly disabled /></FormControl>
                </FormItem>
                <FormField control={editForm.control} name="nombre" render={({ field }) => (
                  <FormItem><FormLabel>Nombre completo</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={editForm.control} name="email" render={({ field }) => (
                  <FormItem><FormLabel>Email</FormLabel><FormControl><Input type="email" {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={editForm.control} name="role" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Rol</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl><SelectTrigger className="w-48"><SelectValue /></SelectTrigger></FormControl>
                      <SelectContent>
                        {ROLES.map((r) => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={editForm.control} name="activo" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Estado</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl><SelectTrigger className="w-48"><SelectValue /></SelectTrigger></FormControl>
                      <SelectContent>
                        <SelectItem value="1">Activo</SelectItem>
                        <SelectItem value="0">Inactivo</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={editForm.control} name="new_password" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nueva contraseña <span className="font-normal text-muted-foreground">(dejar vacío para no cambiar)</span></FormLabel>
                    <FormControl><Input type="password" {...field} placeholder="Mínimo 6 caracteres" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <div className="flex gap-2">
                  <Button type="submit" disabled={saving}><Check />{saving ? 'Guardando…' : 'Guardar cambios'}</Button>
                  <Button type="button" variant="outline" onClick={() => navigate('/usuarios')}>Cancelar</Button>
                </div>
              </form>
            </Form>
          ) : (
            <Form {...createForm}>
              <form className="grid max-w-xl gap-4" onSubmit={createForm.handleSubmit(handleCreate)}>
                <FormField control={createForm.control} name="username" render={({ field }) => (
                  <FormItem><FormLabel>Usuario</FormLabel><FormControl><Input {...field} autoFocus /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={createForm.control} name="nombre" render={({ field }) => (
                  <FormItem><FormLabel>Nombre completo</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={createForm.control} name="email" render={({ field }) => (
                  <FormItem><FormLabel>Email</FormLabel><FormControl><Input type="email" {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={createForm.control} name="role" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Rol</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl><SelectTrigger className="w-48"><SelectValue /></SelectTrigger></FormControl>
                      <SelectContent>
                        {ROLES.map((r) => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={createForm.control} name="password" render={({ field }) => (
                  <FormItem><FormLabel>Contraseña</FormLabel><FormControl><Input type="password" {...field} placeholder="Mínimo 6 caracteres" /></FormControl><FormMessage /></FormItem>
                )} />
                <div className="flex gap-2">
                  <Button type="submit" disabled={saving}><Check />{saving ? 'Guardando…' : 'Crear usuario'}</Button>
                  <Button type="button" variant="outline" onClick={() => navigate('/usuarios')}>Cancelar</Button>
                </div>
              </form>
            </Form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
