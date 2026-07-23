import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, IVA_CONDITIONS, type Egreso, type Proveedor } from '../api'
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
  Truck, Plus, Pencil, Trash2, Eye, Search, X, Inbox,
} from 'lucide-react'

const proveedorSchema = z.object({
  nombre: z.string().trim().min(1, 'El nombre es obligatorio'),
  cuit_dni: z.string().trim().optional(),
  email: z.string().trim().email('Email inválido').optional().or(z.literal('')),
  phone: z.string().trim().optional(),
  address: z.string().trim().optional(),
  iva_condition: z.string().optional(),
})

type ProveedorFormValues = z.infer<typeof proveedorSchema>
const EMPTY_VALUES: ProveedorFormValues = {
  nombre: '', cuit_dni: '', email: '', phone: '', address: '', iva_condition: '',
}

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

export function Proveedores() {
  const [proveedores, setProveedores] = useState<Proveedor[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [saving, setSaving] = useState(false)
  const [q, setQ] = useState('')

  const [viendoId, setViendoId] = useState<number | null>(null)
  const [egresos, setEgresos] = useState<Egreso[]>([])
  const [egresosLoading, setEgresosLoading] = useState(false)

  const form = useForm<ProveedorFormValues>({
    resolver: zodResolver(proveedorSchema),
    defaultValues: EMPTY_VALUES,
  })

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

  function startCreate() {
    setEditingId('new')
    setViendoId(null)
    form.reset(EMPTY_VALUES)
  }

  function startEdit(proveedor: Proveedor) {
    setEditingId(proveedor.id)
    setViendoId(null)
    form.reset({
      nombre: proveedor.nombre,
      cuit_dni: proveedor.cuit_dni ?? '',
      email: proveedor.email ?? '',
      phone: proveedor.phone ?? '',
      address: proveedor.address ?? '',
      iva_condition: proveedor.iva_condition ?? '',
    })
  }

  function cancelEdit() {
    setEditingId(null)
    form.reset(EMPTY_VALUES)
  }

  async function handleSubmit(values: ProveedorFormValues) {
    setSaving(true)
    setError(null)
    const payload = {
      nombre: values.nombre,
      cuit_dni: values.cuit_dni || '',
      email: values.email || '',
      phone: values.phone || '',
      address: values.address || '',
      iva_condition: values.iva_condition || '',
    }
    try {
      if (editingId === 'new') {
        await api.post('/api/proveedores', payload)
      } else if (editingId) {
        await api.put(`/api/proveedores/${editingId}`, payload)
      }
      cancelEdit()
      await loadProveedores()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function eliminar(proveedor: Proveedor) {
    if (!window.confirm(`¿Eliminar este proveedor? Solo es posible si no tiene egresos asociados.`)) return
    setError(null)
    try {
      await api.del(`/api/proveedores/${proveedor.id}`)
      if (viendoId === proveedor.id) setViendoId(null)
      await loadProveedores()
    } catch (err) {
      setError(describeError(err))
    }
  }

  // Restaurado desde web/templates/proveedores/detail.html: egresos
  // asociados a este proveedor. `GET /api/egresos` usa el mes actual como
  // rango por defecto (ver web/api/egresos.py) -- acá se pide un rango
  // amplio explícito para traer el historial completo, igual que mostraba
  // la página vieja.
  async function toggleVer(proveedor: Proveedor) {
    if (viendoId === proveedor.id) {
      setViendoId(null)
      return
    }
    setViendoId(proveedor.id)
    setEgresosLoading(true)
    setError(null)
    try {
      const hoy = new Date().toISOString().slice(0, 10)
      const data = await api.get<{ items: Egreso[] }>(
        `/api/egresos?proveedor_id=${proveedor.id}&desde=2000-01-01&hasta=${hoy}`,
      )
      setEgresos(data.items)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setEgresosLoading(false)
    }
  }

  const columns = useMemo<ColumnDef<Proveedor>[]>(() => [
    { accessorKey: 'nombre', header: sortableHeader('Nombre'), cell: ({ row }) => <span className="font-medium">{row.original.nombre}</span> },
    { accessorKey: 'cuit_dni', header: 'CUIT/DNI', cell: ({ row }) => row.original.cuit_dni || '—' },
    { accessorKey: 'phone', header: 'Teléfono', cell: ({ row }) => row.original.phone || '—' },
    { accessorKey: 'email', header: 'Email', cell: ({ row }) => row.original.email || '—' },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => toggleVer(row.original)}>
            <Eye />{viendoId === row.original.id ? 'Ocultar' : 'Ver'}
          </Button>
          <Button size="sm" variant="outline" onClick={() => startEdit(row.original)}><Pencil />Editar</Button>
          <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}><Trash2 />Eliminar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [viendoId])

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

  const proveedorViendo = proveedores.find((p) => p.id === viendoId)
  const totalEgresos = egresos.reduce((sum, e) => sum + e.total, 0)

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Truck className="size-5 text-primary" />Proveedores</h2>
        {editingId === null && (
          <Button onClick={startCreate}><Plus />Nuevo proveedor</Button>
        )}
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
          <Button size="sm" variant="outline" onClick={() => loadProveedores()}><Search />Buscar</Button>
          {q && <Button size="sm" variant="ghost" onClick={limpiarBusqueda}><X />Limpiar</Button>}
        </CardContent>
      </Card>

      {editingId !== null && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{editingId === 'new' ? 'Nuevo proveedor' : 'Editar proveedor'}</CardTitle>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form className="flex flex-wrap items-start gap-3" onSubmit={form.handleSubmit(handleSubmit)}>
                <FormField
                  control={form.control}
                  name="nombre"
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
                      <FormControl>
                        <Input {...field} className="w-36" />
                      </FormControl>
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
            <DataTable
              columns={columns}
              data={proveedores}
              emptyMessage={q ? `No se encontraron proveedores para "${q}".` : 'Sin proveedores todavía.'}
            />
          )}
        </CardContent>
      </Card>

      {proveedorViendo && (
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base">Egresos de {proveedorViendo.nombre}</CardTitle>
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
      )}
    </div>
  )
}
