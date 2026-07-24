import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import {
  api, ApiError, TIPOS_COMPROBANTE, type CategoriaEgreso, type Egreso, type Proveedor,
} from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form'
import { ArrowUpCircle } from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
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

// Solo alta -- igual que web/templates/egresos/form.html, la edición nunca
// tuvo un punto de entrada en la UI vieja (list.html/detail.html no
// enlazaban a /egresos/{id}/editar).
export function EgresoNuevo() {
  const navigate = useNavigate()
  const [proveedores, setProveedores] = useState<Proveedor[]>([])
  const [categorias, setCategorias] = useState<CategoriaEgreso[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Sin generic explícito en useForm (ver Productos.tsx): z.coerce.number()
  // hace que el tipo de entrada del resolver no coincida con el de salida.
  const form = useForm({ resolver: zodResolver(egresoSchema), defaultValues: EMPTY_VALUES })

  useEffect(() => {
    api.get<Proveedor[]>('/api/proveedores').then(setProveedores).catch(() => {})
    api.get<CategoriaEgreso[]>('/api/egresos/categorias').then(setCategorias).catch(() => {})
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function handleCreate(values: EgresoFormValues) {
    setSaving(true)
    setError(null)
    try {
      const egreso = await api.post<Egreso>('/api/egresos', {
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
      navigate(`/egresos/${egreso.id}`)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <ArrowUpCircle className="size-5 text-destructive" />Nuevo egreso
      </h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader><CardTitle className="text-base">Datos del egreso</CardTitle></CardHeader>
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
                <Button type="button" variant="outline" onClick={() => navigate('/egresos')}>Cancelar</Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}
