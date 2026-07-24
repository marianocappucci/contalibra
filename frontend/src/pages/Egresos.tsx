import { useEffect, useMemo, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, MEDIOS_PAGO_LABELS, TIPOS_COMPROBANTE,
  type Caja, type CategoriaEgreso, type Egreso, type PagoEgreso, type Proveedor, type ResumenEgresos,
} from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  ArrowUpCircle, CheckCircle2, CreditCard, Eye, Filter, Hourglass,
  ListChecks, Plus, Trash2, X,
} from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function firstOfMonthIso(): string {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

const egresoSchema = z.object({
  fecha: z.string(),
  proveedor_id: z.string().optional(),
  concepto: z.string().trim().min(1, 'El concepto es obligatorio'),
  categoria: z.string().trim().optional(),
  tipo_comprobante: z.string(),
  numero: z.string().trim().optional(),
  monto_neto: z.coerce.number().min(0, 'No puede ser negativo'),
  iva_pct: z.coerce.number().min(0, 'No puede ser negativo'),
  observaciones: z.string().trim().optional(),
})
type EgresoFormValues = z.infer<typeof egresoSchema>
const EMPTY_VALUES: EgresoFormValues = {
  fecha: todayIso(), proveedor_id: '', concepto: '', categoria: '',
  tipo_comprobante: 'otro', numero: '', monto_neto: 0, iva_pct: 0, observaciones: '',
}

const pagoSchema = z.object({
  monto: z.coerce.number().min(0.01, 'El monto debe ser mayor a cero'),
  medio_pago: z.string().min(1, 'Elegí un medio de pago'),
  caja_id: z.string().min(1, 'Elegí una caja'),
  fecha: z.string(),
  referencia: z.string().trim().optional(),
})
type PagoFormValues = z.infer<typeof pagoSchema>

export function Egresos() {
  const [desde, setDesde] = useState(firstOfMonthIso())
  const [hasta, setHasta] = useState(todayIso())
  const [categoriaFiltro, setCategoriaFiltro] = useState('')
  const [estadoFiltro, setEstadoFiltro] = useState('')
  const [egresos, setEgresos] = useState<Egreso[]>([])
  const [resumen, setResumen] = useState<ResumenEgresos | null>(null)
  const [proveedores, setProveedores] = useState<Proveedor[]>([])
  const [categorias, setCategorias] = useState<CategoriaEgreso[]>([])
  const [cajas, setCajas] = useState<Caja[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [payingId, setPayingId] = useState<number | null>(null)
  const [abiertoId, setAbiertoId] = useState<number | null>(null)
  const [pagos, setPagos] = useState<PagoEgreso[]>([])
  const [pagosLoading, setPagosLoading] = useState(false)

  // Sin generic explícito en useForm (ver Productos.tsx): z.coerce.number()
  // hace que el tipo de entrada del resolver no coincida con el de salida.
  const form = useForm({ resolver: zodResolver(egresoSchema), defaultValues: EMPTY_VALUES })
  const pagoForm = useForm({
    resolver: zodResolver(pagoSchema),
    defaultValues: { monto: 0, medio_pago: '', caja_id: '', fecha: todayIso(), referencia: '' },
  })

  useEffect(() => {
    api.get<Proveedor[]>('/api/proveedores').then(setProveedores).catch(() => {})
    api.get<Caja[]>('/api/egresos/cajas').then(setCajas).catch(() => {})
    api.get<CategoriaEgreso[]>('/api/egresos/categorias').then(setCategorias).catch(() => {})
  }, [])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desde, hasta, categoriaFiltro, estadoFiltro])

  useEffect(() => {
    if (abiertoId === null) { setPagos([]); return }
    setPagosLoading(true)
    api.get<PagoEgreso[]>(`/api/egresos/${abiertoId}/pagos`)
      .then(setPagos)
      .catch(() => setPagos([]))
      .finally(() => setPagosLoading(false))
  }, [abiertoId])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ desde, hasta })
      if (categoriaFiltro) params.set('categoria', categoriaFiltro)
      if (estadoFiltro) params.set('estado', estadoFiltro)
      const data = await api.get<{ items: Egreso[]; resumen: ResumenEgresos }>(
        `/api/egresos?${params.toString()}`,
      )
      setEgresos(data.items)
      setResumen(data.resumen)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function limpiarFiltros() {
    setCategoriaFiltro('')
    setEstadoFiltro('')
  }

  async function handleCreate(values: EgresoFormValues) {
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/egresos', {
        fecha: values.fecha,
        proveedor_id: values.proveedor_id ? Number(values.proveedor_id) : null,
        concepto: values.concepto,
        categoria: values.categoria || '',
        tipo_comprobante: values.tipo_comprobante,
        numero: values.numero || '',
        monto_neto: values.monto_neto,
        iva_pct: values.iva_pct,
        observaciones: values.observaciones || '',
      })
      setCreating(false)
      form.reset(EMPTY_VALUES)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  function startPagar(egreso: Egreso) {
    setPayingId(egreso.id)
    const caja = cajas.find((c) => c.es_default) ?? cajas[0]
    pagoForm.reset({
      monto: egreso.total,
      medio_pago: caja?.medios_pago[0] ?? '',
      caja_id: caja ? String(caja.id) : '',
      fecha: todayIso(),
      referencia: '',
    })
  }

  async function handlePagar(values: PagoFormValues) {
    if (payingId === null) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/egresos/${payingId}/pagar`, {
        monto: values.monto,
        medio_pago: values.medio_pago,
        caja_id: Number(values.caja_id),
        fecha: values.fecha,
        referencia: values.referencia || '',
      })
      setPayingId(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function eliminar(egreso: Egreso) {
    if (!window.confirm('¿Eliminar este egreso?')) return
    setError(null)
    try {
      await api.del(`/api/egresos/${egreso.id}`)
      if (abiertoId === egreso.id) setAbiertoId(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const estadoBadgeClass: Record<Egreso['estado'], string> = {
    pagado: 'bg-emerald-600 text-white [a&]:hover:bg-emerald-600/90 dark:bg-emerald-500',
    parcial: 'bg-amber-500 text-white [a&]:hover:bg-amber-500/90 dark:bg-amber-600',
    pendiente: '',
  }
  const estadoVariant: Record<Egreso['estado'], 'default' | 'secondary' | 'outline'> = {
    pagado: 'default', parcial: 'default', pendiente: 'secondary',
  }
  const estadoLabel: Record<Egreso['estado'], string> = {
    pagado: 'Pagado', parcial: 'Parcial', pendiente: 'Pendiente',
  }
  const tipoComprobanteLabel: Record<string, string> = Object.fromEntries(
    TIPOS_COMPROBANTE.map((t) => [t.id, t.label]),
  )

  const columns = useMemo<ColumnDef<Egreso>[]>(() => [
    { accessorKey: 'fecha', header: sortableHeader('Fecha') },
    { accessorKey: 'proveedor_nombre', header: 'Proveedor', cell: ({ row }) => row.original.proveedor_nombre || '—' },
    { accessorKey: 'concepto', header: 'Concepto', cell: ({ row }) => <span className="font-medium">{row.original.concepto}</span> },
    { accessorKey: 'categoria', header: 'Categoría', cell: ({ row }) => row.original.categoria || '—' },
    {
      id: 'comprobante',
      header: 'Comprobante',
      cell: ({ row }) => row.original.numero ? <span className="font-mono text-sm">{row.original.numero}</span> : '—',
    },
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
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          {row.original.estado !== 'pagado' && (
            <Button size="sm" variant="outline" onClick={() => startPagar(row.original)}><CreditCard />Pagar</Button>
          )}
          <Button size="sm" variant="outline" onClick={() => setAbiertoId(abiertoId === row.original.id ? null : row.original.id)}>
            <Eye />{abiertoId === row.original.id ? 'Ocultar' : 'Ver'}
          </Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [cajas, abiertoId])

  const egresoAbierto = egresos.find((e) => e.id === abiertoId)
  const totalPagado = pagos.reduce((sum, p) => sum + p.monto, 0)

  const cajaSeleccionada = cajas.find((c) => String(c.id) === pagoForm.watch('caja_id'))

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <ArrowUpCircle className="size-5 text-destructive" />Egresos
        </h2>
        {!creating && <Button onClick={() => setCreating(true)}><Plus />Nuevo egreso</Button>}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {resumen && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card><CardContent className="flex items-start justify-between gap-3">
            <div><CardDescription>Total del período</CardDescription><p className="text-2xl font-bold">{formatCurrency(resumen.total_periodo)}</p></div>
            <span className="shrink-0 rounded-lg bg-muted p-2 text-muted-foreground"><ArrowUpCircle /></span>
          </CardContent></Card>
          <Card><CardContent className="flex items-start justify-between gap-3">
            <div><CardDescription>Pagado</CardDescription><p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{formatCurrency(resumen.pagado)}</p></div>
            <span className="shrink-0 rounded-lg bg-emerald-500/10 p-2 text-emerald-600 dark:text-emerald-400"><CheckCircle2 /></span>
          </CardContent></Card>
          <Card><CardContent className="flex items-start justify-between gap-3">
            <div><CardDescription>Pendiente / Parcial</CardDescription><p className="text-2xl font-bold text-destructive">{formatCurrency(resumen.pendiente)}</p></div>
            <span className="shrink-0 rounded-lg bg-destructive/10 p-2 text-destructive"><Hourglass /></span>
          </CardContent></Card>
        </div>
      )}

      <Card>
        <CardContent className="flex flex-wrap items-end gap-3 py-3">
          <div className="grid gap-1.5">
            <Label>Desde</Label>
            <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="w-40" />
          </div>
          <div className="grid gap-1.5">
            <Label>Hasta</Label>
            <Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="w-40" />
          </div>
          <div className="grid gap-1.5">
            <Label>Categoría</Label>
            <Select value={categoriaFiltro || '__todas__'} onValueChange={(v) => setCategoriaFiltro(v === '__todas__' ? '' : v)}>
              <SelectTrigger className="w-48"><SelectValue placeholder="Todas las categorías" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__todas__">Todas las categorías</SelectItem>
                {categorias.map((c) => <SelectItem key={c.id} value={c.nombre}>{c.nombre}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label>Estado</Label>
            <Select value={estadoFiltro || '__todos__'} onValueChange={(v) => setEstadoFiltro(v === '__todos__' ? '' : v)}>
              <SelectTrigger className="w-40"><SelectValue placeholder="Todos los estados" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__todos__">Todos los estados</SelectItem>
                <SelectItem value="pendiente">Pendiente</SelectItem>
                <SelectItem value="parcial">Parcial</SelectItem>
                <SelectItem value="pagado">Pagado</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button size="sm" variant="outline" onClick={load} title="Filtrar"><Filter /></Button>
          {(categoriaFiltro || estadoFiltro) && (
            <Button size="sm" variant="ghost" onClick={limpiarFiltros} title="Limpiar filtros"><X />Limpiar</Button>
          )}
        </CardContent>
      </Card>

      {creating && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nuevo egreso</CardTitle></CardHeader>
          <CardContent>
            <Form {...form}>
              <form className="grid gap-4" onSubmit={form.handleSubmit(handleCreate)}>
                <div className="flex flex-wrap items-start gap-3">
                  <FormField control={form.control} name="proveedor_id" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Proveedor</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl><SelectTrigger className="w-48"><SelectValue placeholder="Sin proveedor / ocasional" /></SelectTrigger></FormControl>
                        <SelectContent>
                          {proveedores.map((p) => <SelectItem key={p.id} value={String(p.id)}>{p.nombre}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )} />
                  <FormField control={form.control} name="tipo_comprobante" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Comprobante</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl><SelectTrigger className="w-40"><SelectValue /></SelectTrigger></FormControl>
                        <SelectContent>
                          {TIPOS_COMPROBANTE.map((t) => <SelectItem key={t.id} value={t.id}>{t.label}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )} />
                  <FormField control={form.control} name="numero" render={({ field }) => (
                    <FormItem><FormLabel>Número</FormLabel><FormControl><Input {...field} className="w-40 font-mono" placeholder="Ej: 0001-00004523" /></FormControl><FormMessage /></FormItem>
                  )} />
                </div>
                <div className="flex flex-wrap items-start gap-3">
                  <FormField control={form.control} name="concepto" render={({ field }) => (
                    <FormItem className="w-full sm:w-64"><FormLabel>Concepto</FormLabel><FormControl><Input {...field} placeholder="Ej: Alquiler depósito, Factura internet…" /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="categoria" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Categoría</FormLabel>
                      <Select value={field.value || '__sin__'} onValueChange={(v) => field.onChange(v === '__sin__' ? '' : v)}>
                        <FormControl><SelectTrigger className="w-44"><SelectValue placeholder="Sin categoría" /></SelectTrigger></FormControl>
                        <SelectContent>
                          <SelectItem value="__sin__">— Sin categoría —</SelectItem>
                          {categorias.map((c) => <SelectItem key={c.id} value={c.nombre}>{c.nombre}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )} />
                  <FormField control={form.control} name="fecha" render={({ field }) => (
                    <FormItem><FormLabel>Fecha</FormLabel><FormControl><Input type="date" {...field} className="w-40" /></FormControl><FormMessage /></FormItem>
                  )} />
                </div>
                <div className="flex flex-wrap items-end gap-3">
                  <FormField control={form.control} name="monto_neto" render={({ field }) => (
                    <FormItem><FormLabel>Monto neto</FormLabel><FormControl><Input type="number" step="0.01" min={0} {...field} value={field.value as number} className="w-32" /></FormControl><FormMessage /></FormItem>
                  )} />
                  <FormField control={form.control} name="iva_pct" render={({ field }) => (
                    <FormItem>
                      <FormLabel>IVA</FormLabel>
                      <Select value={String(field.value)} onValueChange={(v) => field.onChange(Number(v))}>
                        <FormControl><SelectTrigger className="w-36"><SelectValue /></SelectTrigger></FormControl>
                        <SelectContent>
                          <SelectItem value="0">Sin IVA</SelectItem>
                          <SelectItem value="0.105">10,5%</SelectItem>
                          <SelectItem value="0.21">21%</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )} />
                  <div className="rounded-md bg-muted p-2 text-sm">
                    <p className="flex justify-between gap-4 text-muted-foreground"><span>IVA</span><span>{formatCurrency((Number(form.watch('monto_neto')) || 0) * (Number(form.watch('iva_pct')) || 0))}</span></p>
                    <p className="flex justify-between gap-4 font-bold"><span>Total</span><span className="text-destructive">{formatCurrency((Number(form.watch('monto_neto')) || 0) * (1 + (Number(form.watch('iva_pct')) || 0)))}</span></p>
                  </div>
                </div>
                <FormField control={form.control} name="observaciones" render={({ field }) => (
                  <FormItem><FormLabel>Observaciones</FormLabel><FormControl><Textarea {...field} rows={3} className="max-w-2xl" /></FormControl><FormMessage /></FormItem>
                )} />
                <div className="flex gap-2">
                  <Button type="submit" disabled={saving}>{saving ? 'Guardando…' : 'Guardar egreso'}</Button>
                  <Button type="button" variant="outline" onClick={() => { setCreating(false); form.reset(EMPTY_VALUES) }}>Cancelar</Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>
      )}

      {payingId !== null && (
        <Card>
          <CardHeader><CardTitle className="text-base">Registrar pago</CardTitle></CardHeader>
          <CardContent>
            <Form {...pagoForm}>
              <form className="flex flex-wrap items-start gap-3" onSubmit={pagoForm.handleSubmit(handlePagar)}>
                <FormField control={pagoForm.control} name="fecha" render={({ field }) => (
                  <FormItem><FormLabel>Fecha</FormLabel><FormControl><Input type="date" {...field} className="w-40" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={pagoForm.control} name="monto" render={({ field }) => (
                  <FormItem><FormLabel>Monto</FormLabel><FormControl><Input type="number" step="0.01" {...field} value={field.value as number} className="w-32" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={pagoForm.control} name="caja_id" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Caja</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl><SelectTrigger className="w-40"><SelectValue placeholder="Elegir caja…" /></SelectTrigger></FormControl>
                      <SelectContent>
                        {cajas.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={pagoForm.control} name="medio_pago" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Medio de pago</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl><SelectTrigger className="w-44"><SelectValue placeholder="Elegir medio…" /></SelectTrigger></FormControl>
                      <SelectContent>
                        {(cajaSeleccionada?.medios_pago ?? Object.keys(MEDIOS_PAGO_LABELS)).map((m) => (
                          <SelectItem key={m} value={m}>{MEDIOS_PAGO_LABELS[m] ?? m}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={pagoForm.control} name="referencia" render={({ field }) => (
                  <FormItem><FormLabel>Referencia</FormLabel><FormControl><Input {...field} className="w-40" /></FormControl><FormMessage /></FormItem>
                )} />
                <div className="flex gap-2 pt-6">
                  <Button type="submit" disabled={saving}>{saving ? 'Guardando…' : 'Registrar pago'}</Button>
                  <Button type="button" variant="outline" onClick={() => setPayingId(null)}>Cancelar</Button>
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
            <DataTable columns={columns} data={egresos} emptyMessage="Sin egresos en el período." />
          )}
        </CardContent>
      </Card>

      {egresoAbierto && (() => {
        const e = egresoAbierto
        const pendiente = Math.max(0, e.total - totalPagado)
        return (
          <div className="grid gap-4">
            {e.estado === 'pagado' && (
              <p className="flex items-center gap-2 rounded-md border border-emerald-600/30 bg-emerald-500/10 p-3 text-sm text-emerald-700 dark:text-emerald-400">
                <CheckCircle2 className="size-4 shrink-0" /><strong>Pagado completo</strong> — {formatCurrency(totalPagado)}
              </p>
            )}
            {e.estado === 'parcial' && (
              <p className="flex items-center gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
                <CreditCard className="size-4 shrink-0" /><strong>Pago parcial</strong> — Pagado: {formatCurrency(totalPagado)}
                <span className="font-semibold text-destructive">Pendiente: {formatCurrency(pendiente)}</span>
              </p>
            )}
            {e.estado === 'pendiente' && (
              <p className="flex items-center gap-2 rounded-md border bg-muted/50 p-3 text-sm text-muted-foreground">
                <Hourglass className="size-4 shrink-0" /><strong>Pendiente de pago</strong> — {formatCurrency(e.total)}
              </p>
            )}

            {!pagosLoading && pagos.length > 0 && (
              <Card className="border-l-4 border-l-destructive">
                <CardContent className="py-3">
                  <p className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-destructive">
                    <ListChecks className="size-4" />Pagos registrados
                  </p>
                  <div className="grid gap-1">
                    {pagos.map((p) => (
                      <div key={p.id} className="flex items-center justify-between border-b py-1 text-sm last:border-0">
                        <span className="text-muted-foreground">
                          {p.fecha}
                          {p.medio_pago && <Badge variant="outline" className="ml-1.5">{MEDIOS_PAGO_LABELS[p.medio_pago] ?? p.medio_pago}</Badge>}
                          {p.referencia && <span className="ml-1.5">({p.referencia})</span>}
                        </span>
                        <span className="font-semibold text-destructive">- {formatCurrency(p.monto)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader><CardTitle className="text-base">Datos del egreso</CardTitle></CardHeader>
                <CardContent className="grid gap-1.5 text-sm">
                  <p><span className="text-muted-foreground">Fecha:</span> {e.fecha}</p>
                  {e.proveedor_nombre && <p><span className="text-muted-foreground">Proveedor:</span> {e.proveedor_nombre}</p>}
                  {e.categoria && <p><span className="text-muted-foreground">Categoría:</span> {e.categoria}</p>}
                  <p>
                    <span className="text-muted-foreground">Comprobante:</span> {tipoComprobanteLabel[e.tipo_comprobante] ?? e.tipo_comprobante}
                    {e.numero && <span className="ml-1 font-mono">{e.numero}</span>}
                  </p>
                  {e.observaciones && <p><span className="text-muted-foreground">Observaciones:</span> {e.observaciones}</p>}
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-base">Montos</CardTitle></CardHeader>
                <CardContent className="grid gap-1.5 text-sm">
                  {e.monto_neto > 0 && e.monto_neto !== e.total && (
                    <>
                      <p><span className="text-muted-foreground">Neto:</span> {formatCurrency(e.monto_neto)}</p>
                      <p><span className="text-muted-foreground">IVA ({Math.round(e.iva_pct * 100)}%):</span> {formatCurrency(e.iva_monto)}</p>
                    </>
                  )}
                  <p className="text-base"><span className="text-muted-foreground">Total:</span> <span className="font-bold text-destructive">{formatCurrency(e.total)}</span></p>
                  {pagos.length > 0 && (
                    <>
                      <p><span className="text-muted-foreground">Pagado:</span> <span className="text-emerald-600 dark:text-emerald-400">{formatCurrency(totalPagado)}</span></p>
                      {pendiente > 0 && <p><span className="text-muted-foreground">Pendiente:</span> <span className="font-semibold text-destructive">{formatCurrency(pendiente)}</span></p>}
                    </>
                  )}
                </CardContent>
              </Card>
            </div>

            <div className="flex justify-end pb-4">
              <Button variant="outline" className="text-destructive hover:text-destructive" onClick={() => eliminar(e)}>
                <Trash2 />Eliminar
              </Button>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
