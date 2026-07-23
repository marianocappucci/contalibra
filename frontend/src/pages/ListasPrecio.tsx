import { useEffect, useMemo, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type ItemListaPrecio, type ListaPrecio } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form'
import { DataTable, sortableHeader } from '@/components/data-table'

const listaSchema = z.object({
  nombre: z.string().trim().min(1, 'El nombre es obligatorio'),
  descripcion: z.string().trim().optional(),
})

type ListaFormValues = z.infer<typeof listaSchema>
const EMPTY_VALUES: ListaFormValues = { nombre: '', descripcion: '' }

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

export function ListasPrecio() {
  const [listas, setListas] = useState<ListaPrecio[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [saving, setSaving] = useState(false)

  const [itemsListaId, setItemsListaId] = useState<number | null>(null)
  const [items, setItems] = useState<ItemListaPrecio[]>([])
  const [itemsLoading, setItemsLoading] = useState(false)
  const [precios, setPrecios] = useState<Record<number, string>>({})
  const [savingItems, setSavingItems] = useState(false)

  const form = useForm<ListaFormValues>({
    resolver: zodResolver(listaSchema),
    defaultValues: EMPTY_VALUES,
  })

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

  function startCreate() {
    setEditingId('new')
    form.reset(EMPTY_VALUES)
  }

  function startEdit(lista: ListaPrecio) {
    setEditingId(lista.id)
    form.reset({ nombre: lista.nombre, descripcion: lista.descripcion ?? '' })
  }

  function cancelEdit() {
    setEditingId(null)
    form.reset(EMPTY_VALUES)
  }

  async function handleSubmit(values: ListaFormValues) {
    setSaving(true)
    setError(null)
    try {
      if (editingId === 'new') {
        await api.post('/api/listas-precio', { nombre: values.nombre, descripcion: values.descripcion || '' })
      } else if (editingId) {
        const original = listas.find((l) => l.id === editingId)
        await api.put(`/api/listas-precio/${editingId}`, {
          nombre: values.nombre, descripcion: values.descripcion || '', activa: !!original?.activa,
        })
      }
      cancelEdit()
      await loadListas()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
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
    setError(null)
    try {
      await api.del(`/api/listas-precio/${lista.id}`)
      if (itemsListaId === lista.id) setItemsListaId(null)
      await loadListas()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function verItems(lista: ListaPrecio) {
    if (itemsListaId === lista.id) {
      setItemsListaId(null)
      return
    }
    setItemsListaId(lista.id)
    setItemsLoading(true)
    setError(null)
    try {
      const data = await api.get<ItemListaPrecio[]>(`/api/listas-precio/${lista.id}/items`)
      setItems(data)
      const map: Record<number, string> = {}
      for (const it of data) map[it.id] = it.precio_lista ? String(it.precio_lista) : ''
      setPrecios(map)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setItemsLoading(false)
    }
  }

  async function guardarPrecios() {
    if (itemsListaId === null) return
    setSavingItems(true)
    setError(null)
    try {
      const payload = {
        precios: Object.fromEntries(
          Object.entries(precios)
            .filter(([, v]) => v.trim() !== '')
            .map(([pid, v]) => [pid, Number(v.replace(',', '.'))]),
        ),
      }
      const data = await api.put<ItemListaPrecio[]>(`/api/listas-precio/${itemsListaId}/items`, payload)
      setItems(data)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSavingItems(false)
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
          <Button size="sm" variant="outline" onClick={() => verItems(row.original)}>
            {itemsListaId === row.original.id ? 'Ocultar precios' : 'Ver precios'}
          </Button>
          <Button size="sm" variant="outline" onClick={() => startEdit(row.original)}>Editar</Button>
          <Button size="sm" variant="outline" onClick={() => toggleActiva(row.original)}>
            {row.original.activa ? 'Desactivar' : 'Activar'}
          </Button>
          <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}>Eliminar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [itemsListaId])

  const itemColumns = useMemo<ColumnDef<ItemListaPrecio>[]>(() => [
    { accessorKey: 'nombre', header: 'Producto', cell: ({ row }) => <span className="font-medium">{row.original.nombre}</span> },
    { accessorKey: 'categoria', header: 'Categoría', cell: ({ row }) => row.original.categoria || '—' },
    { accessorKey: 'precio_venta', header: 'Precio de lista general', cell: ({ row }) => formatCurrency(row.original.precio_venta) },
    {
      id: 'precio_lista',
      header: 'Precio en esta lista',
      cell: ({ row }) => (
        <Input
          type="number" step="0.01" className="w-32"
          placeholder={formatCurrency(row.original.precio_venta)}
          value={precios[row.original.id] ?? ''}
          onChange={(e) => setPrecios((p) => ({ ...p, [row.original.id]: e.target.value }))}
        />
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [precios])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Listas de precio</h2>
        {editingId === null && (
          <Button onClick={startCreate}>+ Nueva lista</Button>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {editingId !== null && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{editingId === 'new' ? 'Nueva lista' : 'Editar lista'}</CardTitle>
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
                  name="descripcion"
                  render={({ field }) => (
                    <FormItem className="flex-1">
                      <FormLabel>Descripción</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
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
            <DataTable columns={columns} data={listas} emptyMessage="Sin listas de precio todavía." />
          )}
        </CardContent>
      </Card>

      {itemsListaId !== null && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Precios — {listas.find((l) => l.id === itemsListaId)?.nombre}
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            {itemsLoading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
            ) : (
              <>
                <DataTable columns={itemColumns} data={items} emptyMessage="Sin productos activos." />
                <div>
                  <Button onClick={guardarPrecios} disabled={savingItems}>
                    {savingItems ? 'Guardando…' : 'Guardar precios'}
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
