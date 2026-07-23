import { useEffect, useMemo, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, MEDIOS_PAGO_LABELS, TIPOS_COMPROBANTE,
  type Caja, type Egreso, type Proveedor, type ResumenEgresos,
} from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
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
  const [egresos, setEgresos] = useState<Egreso[]>([])
  const [resumen, setResumen] = useState<ResumenEgresos | null>(null)
  const [proveedores, setProveedores] = useState<Proveedor[]>([])
  const [cajas, setCajas] = useState<Caja[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [payingId, setPayingId] = useState<number | null>(null)

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
  }, [])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desde, hasta])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ items: Egreso[]; resumen: ResumenEgresos }>(
        `/api/egresos?desde=${desde}&hasta=${hasta}`,
      )
      setEgresos(data.items)
      setResumen(data.resumen)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
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
    setError(null)
    try {
      await api.del(`/api/egresos/${egreso.id}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const estadoVariant: Record<Egreso['estado'], 'default' | 'secondary' | 'outline'> = {
    pagado: 'default', parcial: 'secondary', pendiente: 'outline',
  }

  const columns = useMemo<ColumnDef<Egreso>[]>(() => [
    { accessorKey: 'fecha', header: sortableHeader('Fecha') },
    { accessorKey: 'proveedor_nombre', header: 'Proveedor', cell: ({ row }) => row.original.proveedor_nombre || '—' },
    { accessorKey: 'concepto', header: 'Concepto', cell: ({ row }) => <span className="font-medium">{row.original.concepto}</span> },
    { accessorKey: 'categoria', header: 'Categoría', cell: ({ row }) => row.original.categoria || '—' },
    { accessorKey: 'total', header: 'Total', cell: ({ row }) => formatCurrency(row.original.total) },
    {
      accessorKey: 'estado',
      header: 'Estado',
      cell: ({ row }) => <Badge variant={estadoVariant[row.original.estado]}>{row.original.estado}</Badge>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          {row.original.estado !== 'pagado' && (
            <Button size="sm" variant="outline" onClick={() => startPagar(row.original)}>Pagar</Button>
          )}
          <Button size="sm" variant="outline" onClick={() => eliminar(row.original)}>Eliminar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [cajas])

  const cajaSeleccionada = cajas.find((c) => String(c.id) === pagoForm.watch('caja_id'))

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">Egresos</h2>
        <div className="flex items-end gap-3">
          <div className="grid gap-1.5">
            <label className="text-sm font-medium">Desde</label>
            <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="w-40" />
          </div>
          <div className="grid gap-1.5">
            <label className="text-sm font-medium">Hasta</label>
            <Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="w-40" />
          </div>
          {!creating && <Button onClick={() => setCreating(true)}>+ Nuevo egreso</Button>}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {resumen && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card><CardHeader><CardDescription>Total del período</CardDescription><CardTitle className="text-2xl">{formatCurrency(resumen.total_periodo)}</CardTitle></CardHeader></Card>
          <Card><CardHeader><CardDescription>Pagado</CardDescription><CardTitle className="text-2xl text-emerald-600 dark:text-emerald-400">{formatCurrency(resumen.pagado)}</CardTitle></CardHeader></Card>
          <Card><CardHeader><CardDescription>Pendiente</CardDescription><CardTitle className="text-2xl text-destructive">{formatCurrency(resumen.pendiente)}</CardTitle></CardHeader></Card>
        </div>
      )}

      {creating && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nuevo egreso</CardTitle></CardHeader>
          <CardContent>
            <Form {...form}>
              <form className="flex flex-wrap items-start gap-3" onSubmit={form.handleSubmit(handleCreate)}>
                <FormField control={form.control} name="fecha" render={({ field }) => (
                  <FormItem><FormLabel>Fecha</FormLabel><FormControl><Input type="date" {...field} className="w-40" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="proveedor_id" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Proveedor</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl><SelectTrigger className="w-48"><SelectValue placeholder="Sin proveedor" /></SelectTrigger></FormControl>
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
                  <FormItem><FormLabel>Número</FormLabel><FormControl><Input {...field} className="w-32" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="categoria" render={({ field }) => (
                  <FormItem><FormLabel>Categoría</FormLabel><FormControl><Input {...field} className="w-40" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="concepto" render={({ field }) => (
                  <FormItem className="w-full sm:w-64"><FormLabel>Concepto</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="monto_neto" render={({ field }) => (
                  <FormItem><FormLabel>Monto neto</FormLabel><FormControl><Input type="number" step="0.01" {...field} value={field.value as number} className="w-32" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="iva_pct" render={({ field }) => (
                  <FormItem><FormLabel>IVA (ej. 0.21)</FormLabel><FormControl><Input type="number" step="0.01" {...field} value={field.value as number} className="w-28" /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="observaciones" render={({ field }) => (
                  <FormItem className="w-full"><FormLabel>Observaciones</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <div className="flex gap-2 pt-6">
                  <Button type="submit" disabled={saving}>{saving ? 'Guardando…' : 'Crear'}</Button>
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
    </div>
  )
}
