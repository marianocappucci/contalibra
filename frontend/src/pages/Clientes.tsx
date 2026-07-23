import { useEffect, useMemo, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, IVA_CONDITIONS, type Cliente } from '../api'
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
import {
  Users, Plus, Pencil, Eye, Ban, Undo2, Search, Loader2, CheckCircle2, XCircle, IdCard,
} from 'lucide-react'

const clienteSchema = z.object({
  name: z.string().trim().min(1, 'El nombre es obligatorio'),
  address: z.string().trim().optional(),
  cuit_dni: z.string().trim().optional(),
  email: z.string().trim().email('Email inválido').optional().or(z.literal('')),
  phone: z.string().trim().optional(),
  iva_condition: z.string().optional(),
})

type ClienteFormValues = z.infer<typeof clienteSchema>

const EMPTY_VALUES: ClienteFormValues = {
  name: '', address: '', cuit_dni: '', email: '', phone: '', iva_condition: '',
}

export function Clientes() {
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [saving, setSaving] = useState(false)
  const [viendoId, setViendoId] = useState<number | null>(null)

  // Consulta ARCA por CUIT (restaurado desde web/templates/clientes/form.html
  // -- pega contra el mismo endpoint viejo `/api/consultar-cuit/{cuit}`, que
  // sigue vivo en web/app.py sin migrar a este router de la SPA).
  const [consultando, setConsultando] = useState(false)
  const [consultaMsg, setConsultaMsg] = useState<{ tipo: 'ok' | 'error'; texto: string } | null>(null)

  const form = useForm<ClienteFormValues>({
    resolver: zodResolver(clienteSchema),
    defaultValues: EMPTY_VALUES,
  })

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

  function startCreate() {
    setEditingId('new')
    setViendoId(null)
    setConsultaMsg(null)
    form.reset(EMPTY_VALUES)
  }

  function startEdit(cliente: Cliente) {
    setEditingId(cliente.id)
    setViendoId(null)
    setConsultaMsg(null)
    form.reset({
      name: cliente.name,
      address: cliente.address ?? '',
      cuit_dni: cliente.cuit_dni ?? '',
      email: cliente.email ?? '',
      phone: cliente.phone ?? '',
      iva_condition: cliente.iva_condition ?? '',
    })
  }

  function cancelEdit() {
    setEditingId(null)
    setConsultaMsg(null)
    form.reset(EMPTY_VALUES)
  }

  function toggleVer(cliente: Cliente) {
    setViendoId((id) => (id === cliente.id ? null : cliente.id))
  }

  async function handleSubmit(values: ClienteFormValues) {
    setSaving(true)
    setError(null)
    const payload = {
      name: values.name,
      address: values.address || '',
      cuit_dni: values.cuit_dni || '',
      email: values.email || '',
      phone: values.phone || '',
      iva_condition: values.iva_condition || '',
    }
    try {
      if (editingId === 'new') {
        await api.post('/api/clientes', payload)
      } else if (editingId) {
        await api.put(`/api/clientes/${editingId}`, payload)
      }
      cancelEdit()
      await loadClientes()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function toggleActivo(cliente: Cliente) {
    if (cliente.activo && !window.confirm(`¿Desactivar a ${cliente.name}?`)) return
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

  // Restaurado desde web/templates/clientes/form.html (btn-consultar): trae
  // nombre/domicilio/condición IVA desde ARCA por CUIT y completa el
  // formulario. El endpoint devuelve {error} en vez de {detail} en fallas,
  // por eso no se usa api.get acá -- se parsea la respuesta a mano igual
  // que hacía el script vanilla original.
  async function consultarCuit() {
    const cuit = (form.getValues('cuit_dni') || '').replace(/\D/g, '')
    if (cuit.length !== 11) {
      setConsultaMsg({ tipo: 'error', texto: 'Ingresá un CUIT de 11 dígitos antes de consultar.' })
      return
    }
    setConsultando(true)
    setConsultaMsg(null)
    try {
      const resp = await fetch(`/api/consultar-cuit/${cuit}`, { credentials: 'include' })
      const data = await resp.json()
      if (!resp.ok || data.error) {
        setConsultaMsg({ tipo: 'error', texto: data.error || 'Error al consultar ARCA.' })
      } else {
        if (data.nombre) form.setValue('name', data.nombre)
        if (data.domicilio) form.setValue('address', data.domicilio)
        if (data.iva_condition && (IVA_CONDITIONS as readonly string[]).includes(data.iva_condition)) {
          form.setValue('iva_condition', data.iva_condition)
        }
        const estado = data.estado ? ` — Estado: ${data.estado}` : ''
        setConsultaMsg({ tipo: 'ok', texto: `Datos importados desde ARCA${estado}.` })
      }
    } catch {
      setConsultaMsg({ tipo: 'error', texto: 'No se pudo conectar con ARCA.' })
    } finally {
      setConsultando(false)
    }
  }

  const columns = useMemo<ColumnDef<Cliente>[]>(() => [
    { accessorKey: 'name', header: sortableHeader('Nombre'), cell: ({ row }) => (
      <span className="font-medium">
        {row.original.name}
        {!row.original.activo && <Badge variant="outline" className="ml-2">Inactivo</Badge>}
      </span>
    ) },
    { accessorKey: 'cuit_dni', header: 'CUIT/DNI', cell: ({ row }) => row.original.cuit_dni || '—' },
    { accessorKey: 'phone', header: 'Teléfono', cell: ({ row }) => row.original.phone || '—' },
    { accessorKey: 'email', header: 'Email', cell: ({ row }) => row.original.email || '—' },
    { accessorKey: 'iva_condition', header: 'Condición IVA', cell: ({ row }) => row.original.iva_condition || '—' },
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
          <Button size="sm" variant="outline" onClick={() => toggleVer(row.original)}>
            <Eye />{viendoId === row.original.id ? 'Ocultar' : 'Ver'}
          </Button>
          {row.original.activo && (
            <Button size="sm" variant="outline" onClick={() => startEdit(row.original)}><Pencil />Editar</Button>
          )}
          <Button size="sm" variant="outline" onClick={() => toggleActivo(row.original)}>
            {row.original.activo ? <><Ban />Desactivar</> : <><Undo2 />Reactivar</>}
          </Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [viendoId])

  const clienteViendo = clientes.find((c) => c.id === viendoId)

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Users className="size-5 text-primary" />Clientes</h2>
        {editingId === null && (
          <Button onClick={startCreate}><Plus />Nuevo cliente</Button>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {editingId !== null && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{editingId === 'new' ? 'Nuevo cliente' : 'Editar cliente'}</CardTitle>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form className="flex flex-wrap items-start gap-3" onSubmit={form.handleSubmit(handleSubmit)}>
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Nombre</FormLabel>
                      <FormControl>
                        <Input {...field} className="w-48" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="cuit_dni"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>CUIT/DNI</FormLabel>
                      <div className="flex gap-1.5">
                        <FormControl>
                          <Input {...field} className="w-36" placeholder="20-12345678-9" />
                        </FormControl>
                        <Button
                          type="button" size="sm" variant="outline" disabled={consultando}
                          onClick={consultarCuit} title="Consultar datos en ARCA"
                        >
                          {consultando ? <Loader2 className="animate-spin" /> : <Search />}
                        </Button>
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="phone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Teléfono</FormLabel>
                      <FormControl>
                        <Input {...field} className="w-36" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Email</FormLabel>
                      <FormControl>
                        <Input type="email" {...field} className="w-52" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Dirección</FormLabel>
                      <FormControl>
                        <Input {...field} className="w-52" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="iva_condition"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Condición de IVA</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger className="w-52">
                            <SelectValue placeholder="Condición de IVA…" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {IVA_CONDITIONS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                {consultaMsg && (
                  <p className={`flex w-full items-center gap-1.5 text-sm ${consultaMsg.tipo === 'ok' ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}`}>
                    {consultaMsg.tipo === 'ok' ? <CheckCircle2 className="size-4 shrink-0" /> : <XCircle className="size-4 shrink-0" />}
                    {consultaMsg.texto}
                  </p>
                )}
                <div className="flex gap-2 pt-6">
                  <Button type="submit" disabled={saving}>
                    {saving ? 'Guardando…' : editingId === 'new' ? 'Crear' : 'Guardar'}
                  </Button>
                  <Button type="button" variant="outline" onClick={cancelEdit}>Cancelar</Button>
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
            <DataTable columns={columns} data={clientes} emptyMessage="Sin clientes todavía." />
          )}
        </CardContent>
      </Card>

      {clienteViendo && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <IdCard className="size-4 text-primary" />Ficha de {clienteViendo.name}
              {!clienteViendo.activo && <Badge variant="outline">Inactivo</Badge>}
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-1.5 text-sm">
            <p><span className="text-muted-foreground">Nombre / Razón social:</span> <span className="font-medium">{clienteViendo.name}</span></p>
            {clienteViendo.cuit_dni && <p><span className="text-muted-foreground">CUIT / DNI:</span> <span className="font-mono">{clienteViendo.cuit_dni}</span></p>}
            {clienteViendo.iva_condition && <p><span className="text-muted-foreground">Condición IVA:</span> {clienteViendo.iva_condition}</p>}
            {clienteViendo.address && <p><span className="text-muted-foreground">Domicilio:</span> {clienteViendo.address}</p>}
            {clienteViendo.phone && <p><span className="text-muted-foreground">Teléfono:</span> {clienteViendo.phone}</p>}
            {clienteViendo.email && <p><span className="text-muted-foreground">Email:</span> <a className="underline" href={`mailto:${clienteViendo.email}`}>{clienteViendo.email}</a></p>}
            <p><span className="text-muted-foreground">Facturación automática MP:</span> {clienteViendo.auto_facturar ? 'Activa' : 'Inactiva'}</p>
            <p className="mt-2 text-xs text-muted-foreground">
              Las facturas, presupuestos y remitos asociados a este cliente, y los alias de facturación de
              Mercado Pago, todavía no tienen un endpoint en la API de la SPA (existían en la página de
              detalle Jinja2 vieja vía <code>/clientes/&#123;id&#125;</code>) — ver reporte de auditoría.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
