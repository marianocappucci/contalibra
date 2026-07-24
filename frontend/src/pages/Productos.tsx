import { useEffect, useMemo, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, UNIDADES, type CategoriaProducto, type Producto } from '../api'
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
import { Switch } from '@/components/ui/switch'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  Package, Plus, Pencil, Trash2, Search, X, TrendingUp,
} from 'lucide-react'

const productoSchema = z.object({
  nombre: z.string().trim().min(1, 'El nombre es obligatorio'),
  codigo: z.string().trim().optional(),
  descripcion: z.string().trim().optional(),
  precio_venta: z.coerce.number().min(0, 'No puede ser negativo'),
  precio_costo: z.coerce.number().min(0, 'No puede ser negativo'),
  unidad: z.string(),
  categoria: z.string().trim().optional(),
  stock_minimo: z.coerce.number().min(0, 'No puede ser negativo'),
  // Solo se edita en el form de edición (checkbox "Producto activo" de
  // web/templates/productos/form.html) -- en alta siempre nace activo.
  activo: z.boolean(),
})

type ProductoFormValues = z.infer<typeof productoSchema>

const EMPTY_VALUES: ProductoFormValues = {
  nombre: '', codigo: '', descripcion: '', precio_venta: 0, precio_costo: 0,
  unidad: 'u', categoria: '', stock_minimo: 0, activo: true,
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

export function Productos() {
  const [productos, setProductos] = useState<Producto[]>([])
  const [categorias, setCategorias] = useState<CategoriaProducto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [saving, setSaving] = useState(false)
  const [q, setQ] = useState('')

  // Sin generic explícito en useForm: con z.coerce.number() el tipo de
  // entrada del resolver (string|unknown) difiere del tipo de salida
  // (number) -- dejar que TS infiera el tipo desde el resolver evita el
  // choque de tipos entre ambos.
  const form = useForm({
    resolver: zodResolver(productoSchema),
    defaultValues: EMPTY_VALUES,
  })

  // Margen en vivo (restaurado desde web/templates/productos/form.html).
  const precioVenta = Number(form.watch('precio_venta')) || 0
  const precioCosto = Number(form.watch('precio_costo')) || 0
  const margen = precioCosto > 0 && precioVenta > 0 ? ((precioVenta - precioCosto) / precioCosto) * 100 : null

  useEffect(() => {
    loadProductos()
    api.get<CategoriaProducto[]>('/api/productos/categorias').then(setCategorias).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function loadProductos(query = q) {
    setLoading(true)
    setError(null)
    try {
      const path = query ? `/api/productos?q=${encodeURIComponent(query)}` : '/api/productos'
      setProductos(await api.get<Producto[]>(path))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function limpiarBusqueda() {
    setQ('')
    loadProductos('')
  }

  function startCreate() {
    setEditingId('new')
    form.reset(EMPTY_VALUES)
  }

  function startEdit(producto: Producto) {
    setEditingId(producto.id)
    form.reset({
      nombre: producto.nombre,
      codigo: producto.codigo ?? '',
      descripcion: producto.descripcion ?? '',
      precio_venta: producto.precio_venta,
      precio_costo: producto.precio_costo,
      unidad: producto.unidad || 'u',
      categoria: producto.categoria ?? '',
      stock_minimo: producto.stock_minimo,
      activo: !!producto.activo,
    })
  }

  function cancelEdit() {
    setEditingId(null)
    form.reset(EMPTY_VALUES)
  }

  async function handleSubmit(values: ProductoFormValues) {
    setSaving(true)
    setError(null)
    const payload = {
      nombre: values.nombre,
      codigo: values.codigo || '',
      descripcion: values.descripcion || '',
      precio_venta: values.precio_venta,
      precio_costo: values.precio_costo,
      unidad: values.unidad,
      categoria: values.categoria || '',
      stock_minimo: values.stock_minimo,
      // Alta: siempre nace activo. Edición: viaja el switch "Producto
      // activo" del form, igual que el checkbox de
      // web/templates/productos/form.html -- reactivar/desactivar un
      // producto se hace editándolo, no hay botón aparte en la lista vieja.
      activo: editingId === 'new' ? true : values.activo,
    }
    try {
      if (editingId === 'new') {
        await api.post('/api/productos', payload)
      } else if (editingId) {
        await api.put(`/api/productos/${editingId}`, payload)
      }
      cancelEdit()
      await loadProductos()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  // Restaurado desde web/templates/productos/list.html -- el DELETE físico
  // ya existe en el backend (web/api/productos.py) pero no estaba wireado
  // en esta página, solo quedaba el toggle activo/inactivo.
  async function eliminar(producto: Producto) {
    if (!window.confirm(`¿Eliminar ${producto.nombre}?`)) return
    setError(null)
    try {
      await api.del(`/api/productos/${producto.id}`)
      await loadProductos()
    } catch (err) {
      setError(describeError(err))
    }
  }

  // Orden y columnas igual a web/templates/productos/list.html: Código,
  // Nombre, Categoría, Unidad, Precio venta, Precio costo, Estado, acciones
  // (Unidad va antes de los precios, no después).
  const columns = useMemo<ColumnDef<Producto>[]>(() => [
    { accessorKey: 'codigo', header: 'Código', cell: ({ row }) => <span className="font-mono text-xs">{row.original.codigo || '—'}</span> },
    { accessorKey: 'nombre', header: sortableHeader('Nombre'), cell: ({ row }) => <span className="font-medium">{row.original.nombre}</span> },
    { accessorKey: 'categoria', header: 'Categoría', cell: ({ row }) => row.original.categoria || '—' },
    { accessorKey: 'unidad', header: 'Unidad' },
    { accessorKey: 'precio_venta', header: 'Precio venta', cell: ({ row }) => formatCurrency(row.original.precio_venta) },
    { accessorKey: 'precio_costo', header: 'Precio costo', cell: ({ row }) => <span className="text-muted-foreground">{formatCurrency(row.original.precio_costo)}</span> },
    {
      accessorKey: 'activo',
      header: () => <div className="text-center">Estado</div>,
      cell: ({ row }) => (
        <div className="text-center">
          <Badge variant={row.original.activo ? 'default' : 'secondary'}>
            {row.original.activo ? 'Activo' : 'Inactivo'}
          </Badge>
        </div>
      ),
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => startEdit(row.original)}><Pencil />Editar</Button>
          <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}><Trash2 />Eliminar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Package className="size-5 text-primary" />Productos</h2>
        {editingId === null && (
          <Button onClick={startCreate}><Plus />Nuevo producto</Button>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardContent className="flex flex-wrap items-center gap-2 py-3">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadProductos()}
            placeholder="Buscar por nombre, código o categoría…"
            className="w-72"
          />
          <Button size="sm" variant="outline" onClick={() => loadProductos()}><Search />Buscar</Button>
          {q && <Button size="sm" variant="ghost" onClick={limpiarBusqueda}><X />Limpiar</Button>}
        </CardContent>
      </Card>

      {editingId !== null && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{editingId === 'new' ? 'Nuevo producto' : 'Editar producto'}</CardTitle>
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
                  name="codigo"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Código</FormLabel>
                      <FormControl>
                        <Input {...field} className="w-32" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="categoria"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Categoría</FormLabel>
                      <FormControl>
                        <Input {...field} className="w-40" list="categorias-producto" placeholder="Elegir o escribir…" />
                      </FormControl>
                      <datalist id="categorias-producto">
                        {categorias.map((c) => <option key={c.id} value={c.nombre} />)}
                      </datalist>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="unidad"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Unidad</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger className="w-28">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {UNIDADES.map((u) => <SelectItem key={u} value={u}>{u}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="precio_venta"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Precio de venta</FormLabel>
                      <FormControl>
                        <Input type="number" step="0.01" {...field} value={field.value as number} className="w-32" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="precio_costo"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Precio de costo</FormLabel>
                      <FormControl>
                        <Input type="number" step="0.01" {...field} value={field.value as number} className="w-32" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="stock_minimo"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Stock mínimo</FormLabel>
                      <FormControl>
                        <Input type="number" step="0.01" {...field} value={field.value as number} className="w-28" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="descripcion"
                  render={({ field }) => (
                    <FormItem className="w-full">
                      <FormLabel>Descripción</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                {margen !== null && (
                  <p className={`flex w-full items-center gap-1.5 text-sm ${margen >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}`}>
                    <TrendingUp className="size-4 shrink-0" />Margen: <strong>{margen.toFixed(1)}%</strong>
                  </p>
                )}
                {editingId !== 'new' && (
                  <FormField
                    control={form.control}
                    name="activo"
                    render={({ field }) => (
                      <FormItem className="flex w-full flex-row items-center gap-2 space-y-0">
                        <FormControl>
                          <Switch checked={field.value} onCheckedChange={field.onChange} />
                        </FormControl>
                        <FormLabel className="!mt-0">Producto activo</FormLabel>
                      </FormItem>
                    )}
                  />
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
            <DataTable
              columns={columns}
              data={productos}
              emptyMessage={q ? `No se encontraron productos para "${q}".` : 'No hay productos registrados aún.'}
              getRowClassName={(p) => !p.activo ? 'opacity-60' : undefined}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
