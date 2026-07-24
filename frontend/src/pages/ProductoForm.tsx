import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { api, ApiError, UNIDADES, type CategoriaProducto, type Producto } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form'
import { Switch } from '@/components/ui/switch'
import { Package, TrendingUp } from 'lucide-react'

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

const EMPTY_VALUES = {
  nombre: '', codigo: '', descripcion: '', precio_venta: 0, precio_costo: 0,
  unidad: 'u', categoria: '', stock_minimo: 0, activo: true,
}

// Misma página para alta y edición, igual que web/templates/productos/form.html
// viejo -- si hay :id en la ruta (/productos/:id/editar) precarga el producto
// existente. No existe un GET /api/productos/{id} en el backend (ver
// web/api/productos.py) -- se trae la lista completa y se busca el id.
export function ProductoForm() {
  const { id } = useParams<{ id: string }>()
  const editingId = id ? Number(id) : null
  const navigate = useNavigate()

  const [categorias, setCategorias] = useState<CategoriaProducto[]>([])
  const [loadingProducto, setLoadingProducto] = useState(Boolean(editingId))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  useEffect(() => {
    api.get<CategoriaProducto[]>('/api/productos/categorias').then(setCategorias).catch(() => {})
  }, [])

  useEffect(() => {
    if (!editingId) return
    api.get<Producto[]>('/api/productos').then((productos) => {
      const producto = productos.find((p) => p.id === editingId)
      if (!producto) {
        setError('Producto no encontrado')
        return
      }
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
    }).catch((err) => setError(describeError(err))).finally(() => setLoadingProducto(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingId])

  async function handleSubmit(values: z.infer<typeof productoSchema>) {
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
      activo: editingId ? values.activo : true,
    }
    try {
      const producto = editingId
        ? await api.put<Producto>(`/api/productos/${editingId}`, payload)
        : await api.post<Producto>('/api/productos', payload)
      void producto
      navigate('/productos')
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <Package className="size-5 text-primary" />{editingId ? 'Editar producto' : 'Nuevo producto'}
      </h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loadingProducto ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <Card>
          <CardHeader><CardTitle className="text-base">Datos del producto</CardTitle></CardHeader>
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
                {editingId && (
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
                    {saving ? 'Guardando…' : editingId ? 'Guardar cambios' : 'Crear producto'}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => navigate('/productos')}>Cancelar</Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
