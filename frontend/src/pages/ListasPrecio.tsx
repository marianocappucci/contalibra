import { useEffect, useMemo, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type CategoriaProducto, type ItemListaPrecio, type ListaPrecio } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form'
import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter, SheetClose,
} from '@/components/ui/sheet'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  Tag, Plus, Pencil, Trash2, Eye, Ban, Undo2, Percent, Download,
} from 'lucide-react'

const listaSchema = z.object({
  nombre: z.string().trim().min(1, 'El nombre es obligatorio'),
  descripcion: z.string().trim().optional(),
})

type ListaFormValues = z.infer<typeof listaSchema>
const EMPTY_VALUES: ListaFormValues = { nombre: '', descripcion: '' }

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

function margenPct(precio: number, costo: number): string {
  if (!precio || !costo) return '—'
  return `${(((precio / costo) - 1) * 100).toFixed(1)}%`
}

export function ListasPrecio() {
  const [listas, setListas] = useState<ListaPrecio[]>([])
  const [categorias, setCategorias] = useState<CategoriaProducto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [saving, setSaving] = useState(false)

  const [itemsListaId, setItemsListaId] = useState<number | null>(null)
  const [items, setItems] = useState<ItemListaPrecio[]>([])
  const [itemsLoading, setItemsLoading] = useState(false)
  const [precios, setPrecios] = useState<Record<number, string>>({})
  const [savingItems, setSavingItems] = useState(false)
  const [categoriaFiltro, setCategoriaFiltro] = useState('')

  // Actualizar en lote / Importar precios -- restaurados desde
  // web/templates/listas_precio/detail.html (modales Bootstrap). Los
  // endpoints ya existían en web/api/listas_precio.py sin usar desde la SPA.
  const [loteOpen, setLoteOpen] = useState(false)
  const [loteBase, setLoteBase] = useState<'lista' | 'venta' | 'costo'>('lista')
  const [lotePorcentaje, setLotePorcentaje] = useState('')
  const [loteCategoria, setLoteCategoria] = useState('')
  const [loteSaving, setLoteSaving] = useState(false)

  const [importOpen, setImportOpen] = useState(false)
  const [importFuente, setImportFuente] = useState<'venta' | 'costo' | 'lista'>('venta')
  const [importFuenteListaId, setImportFuenteListaId] = useState('')
  const [importSaving, setImportSaving] = useState(false)

  const form = useForm<ListaFormValues>({
    resolver: zodResolver(listaSchema),
    defaultValues: EMPTY_VALUES,
  })

  useEffect(() => {
    loadListas()
    api.get<CategoriaProducto[]>('/api/productos/categorias').then(setCategorias).catch(() => {})
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
    if (!window.confirm('¿Eliminar esta lista y todos sus precios?')) return
    setError(null)
    try {
      await api.del(`/api/listas-precio/${lista.id}`)
      if (itemsListaId === lista.id) setItemsListaId(null)
      await loadListas()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function cargarItems(listaId: number, categoria: string) {
    setItemsLoading(true)
    setError(null)
    try {
      const path = categoria
        ? `/api/listas-precio/${listaId}/items?categoria=${encodeURIComponent(categoria)}`
        : `/api/listas-precio/${listaId}/items`
      const data = await api.get<ItemListaPrecio[]>(path)
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

  async function verItems(lista: ListaPrecio) {
    if (itemsListaId === lista.id) {
      setItemsListaId(null)
      return
    }
    setItemsListaId(lista.id)
    setCategoriaFiltro('')
    await cargarItems(lista.id, '')
  }

  async function aplicarFiltroCategoria(categoria: string) {
    setCategoriaFiltro(categoria)
    if (itemsListaId !== null) await cargarItems(itemsListaId, categoria)
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

  function abrirLote() {
    setLoteBase('lista')
    setLotePorcentaje('')
    setLoteCategoria(categoriaFiltro)
    setLoteOpen(true)
  }

  async function aplicarLote() {
    if (itemsListaId === null) return
    const pct = Number(lotePorcentaje.replace(',', '.'))
    if (Number.isNaN(pct)) {
      setError('Ingresá un porcentaje válido.')
      return
    }
    setLoteSaving(true)
    setError(null)
    try {
      await api.post(`/api/listas-precio/${itemsListaId}/ajuste-porcentual`, {
        porcentaje: pct, base: loteBase, categoria: loteCategoria,
      })
      setLoteOpen(false)
      await cargarItems(itemsListaId, categoriaFiltro)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoteSaving(false)
    }
  }

  function abrirImportar() {
    setImportFuente('venta')
    setImportFuenteListaId('')
    setImportOpen(true)
  }

  async function aplicarImportar() {
    if (itemsListaId === null) return
    if (importFuente === 'lista' && !importFuenteListaId) {
      setError('Elegí la lista de origen.')
      return
    }
    setImportSaving(true)
    setError(null)
    try {
      const data = await api.post<ItemListaPrecio[]>(`/api/listas-precio/${itemsListaId}/importar`, {
        fuente: importFuente,
        fuente_lista_id: importFuente === 'lista' ? Number(importFuenteListaId) : null,
      })
      setItems(data)
      const map: Record<number, string> = {}
      for (const it of data) map[it.id] = it.precio_lista ? String(it.precio_lista) : ''
      setPrecios(map)
      setImportOpen(false)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setImportSaving(false)
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
            <Eye />{itemsListaId === row.original.id ? 'Ocultar precios' : 'Ver precios'}
          </Button>
          <Button size="sm" variant="outline" onClick={() => startEdit(row.original)}><Pencil />Editar</Button>
          <Button size="sm" variant="outline" onClick={() => toggleActiva(row.original)}>
            {row.original.activa ? <><Ban />Desactivar</> : <><Undo2 />Activar</>}
          </Button>
          <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}><Trash2 />Eliminar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [itemsListaId])

  const itemColumns = useMemo<ColumnDef<ItemListaPrecio>[]>(() => [
    { accessorKey: 'codigo', header: 'Código', cell: ({ row }) => <span className="font-mono text-xs">{row.original.codigo || '—'}</span> },
    { accessorKey: 'nombre', header: 'Producto', cell: ({ row }) => <span className="font-medium">{row.original.nombre}</span> },
    { accessorKey: 'categoria', header: 'Categoría', cell: ({ row }) => row.original.categoria || '—' },
    { accessorKey: 'precio_costo', header: 'P. Costo', cell: ({ row }) => <span className="text-muted-foreground">{formatCurrency(row.original.precio_costo)}</span> },
    { accessorKey: 'precio_venta', header: 'P. Venta', cell: ({ row }) => <span className="text-muted-foreground">{formatCurrency(row.original.precio_venta)}</span> },
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
    {
      id: 'margen',
      header: 'Margen',
      cell: ({ row }) => {
        const precio = Number(precios[row.original.id]) || row.original.precio_venta
        const label = margenPct(precio, row.original.precio_costo)
        const cls = label === '—' ? 'text-muted-foreground' : precio >= row.original.precio_costo ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'
        return <span className={`text-sm ${cls}`}>{label}</span>
      },
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [precios])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Tag className="size-5 text-primary" />Listas de precio</h2>
        {editingId === null && (
          <Button onClick={startCreate}><Plus />Nueva lista</Button>
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
          <CardHeader className="flex-row flex-wrap items-center justify-between gap-3 space-y-0">
            <CardTitle className="text-base">
              Precios — {listas.find((l) => l.id === itemsListaId)?.nombre}
            </CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <Select value={categoriaFiltro || '__todas__'} onValueChange={(v) => aplicarFiltroCategoria(v === '__todas__' ? '' : v)}>
                <SelectTrigger className="w-48"><SelectValue placeholder="Todas las categorías" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__todas__">Todas las categorías</SelectItem>
                  {categorias.map((c) => <SelectItem key={c.id} value={c.nombre}>{c.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
              <Button size="sm" variant="outline" onClick={abrirLote}><Percent />Actualizar en lote</Button>
              <Button size="sm" variant="outline" onClick={abrirImportar}><Download />Importar precios</Button>
            </div>
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

      {/* Actualizar en lote -- restaurado desde el modal #modalLote de web/templates/listas_precio/detail.html */}
      <Sheet open={loteOpen} onOpenChange={setLoteOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2"><Percent className="size-4" />Actualizar precios en lote</SheetTitle>
          </SheetHeader>
          <div className="grid gap-4 px-4">
            <div className="grid gap-1.5">
              <Label>Base de cálculo</Label>
              <Select value={loteBase} onValueChange={(v) => setLoteBase(v as typeof loteBase)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="lista">Precios actuales de esta lista</SelectItem>
                  <SelectItem value="venta">Precio de venta de cada producto</SelectItem>
                  <SelectItem value="costo">Precio de costo de cada producto</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label>Porcentaje de ajuste</Label>
              <Input
                type="number" step="0.1" value={lotePorcentaje}
                onChange={(e) => setLotePorcentaje(e.target.value)}
                placeholder="Ej: 10 para +10%, -5 para -5%"
              />
            </div>
            <div className="grid gap-1.5">
              <Label>Aplicar a</Label>
              <Select value={loteCategoria || '__todas__'} onValueChange={(v) => setLoteCategoria(v === '__todas__' ? '' : v)}>
                <SelectTrigger><SelectValue placeholder="Todos los productos" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__todas__">Todos los productos</SelectItem>
                  {categorias.map((c) => <SelectItem key={c.id} value={c.nombre}>{c.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <p className="text-sm text-muted-foreground">
              Esta acción reemplaza los precios calculados. Los precios que no estén en la lista se van a insertar.
            </p>
          </div>
          <SheetFooter className="flex-row justify-end gap-2">
            <SheetClose asChild><Button variant="outline">Cancelar</Button></SheetClose>
            <Button onClick={aplicarLote} disabled={loteSaving}>{loteSaving ? 'Aplicando…' : 'Aplicar'}</Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Importar precios -- restaurado desde el modal #modalImportar de web/templates/listas_precio/detail.html */}
      <Sheet open={importOpen} onOpenChange={setImportOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2"><Download className="size-4" />Importar precios</SheetTitle>
          </SheetHeader>
          <div className="grid gap-4 px-4">
            <p className="text-sm text-muted-foreground">
              Reemplaza los precios existentes en esta lista con los precios de la fuente seleccionada.
            </p>
            <div className="grid gap-1.5">
              <Label>Importar desde</Label>
              <Select value={importFuente} onValueChange={(v) => setImportFuente(v as typeof importFuente)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="venta">Precio de venta de cada producto</SelectItem>
                  <SelectItem value="costo">Precio de costo de cada producto</SelectItem>
                  <SelectItem value="lista">Desde otra lista</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {importFuente === 'lista' && (
              <div className="grid gap-1.5">
                <Label>Lista de origen</Label>
                <Select value={importFuenteListaId} onValueChange={setImportFuenteListaId}>
                  <SelectTrigger><SelectValue placeholder="Elegir lista…" /></SelectTrigger>
                  <SelectContent>
                    {listas.filter((l) => l.id !== itemsListaId).map((l) => (
                      <SelectItem key={l.id} value={String(l.id)}>{l.nombre}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          <SheetFooter className="flex-row justify-end gap-2">
            <SheetClose asChild><Button variant="outline">Cancelar</Button></SheetClose>
            <Button onClick={aplicarImportar} disabled={importSaving}>{importSaving ? 'Importando…' : 'Importar'}</Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  )
}
