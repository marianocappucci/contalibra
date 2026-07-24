import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { api, ApiError, type ListaPrecio } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Tag } from 'lucide-react'

const listaSchema = z.object({
  nombre: z.string().trim().min(1, 'El nombre es obligatorio'),
  descripcion: z.string().trim().optional(),
})
type ListaFormValues = z.infer<typeof listaSchema>
const EMPTY_VALUES: ListaFormValues = { nombre: '', descripcion: '' }

// Solo alta -- igual que web/templates/listas_precio/form.html, que no
// manejaba edición (el nombre/descripción/activa se editan desde el modal
// "Configurar" de ListaPrecioDetalle.tsx, ruta /listas-precio/:id).
export function ListaPrecioNueva() {
  const navigate = useNavigate()
  const [listas, setListas] = useState<ListaPrecio[]>([])
  const [importarInicial, setImportarInicial] = useState<'' | 'venta' | 'costo' | 'lista'>('')
  const [importarInicialListaId, setImportarInicialListaId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const form = useForm<ListaFormValues>({ resolver: zodResolver(listaSchema), defaultValues: EMPTY_VALUES })

  useEffect(() => {
    api.get<ListaPrecio[]>('/api/listas-precio').then(setListas).catch(() => {})
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function handleSubmit(values: ListaFormValues) {
    setSaving(true)
    setError(null)
    try {
      const nueva = await api.post<ListaPrecio>('/api/listas-precio', { nombre: values.nombre, descripcion: values.descripcion || '' })
      if (importarInicial) {
        await api.post(`/api/listas-precio/${nueva.id}/importar`, {
          fuente: importarInicial,
          fuente_lista_id: importarInicial === 'lista' ? Number(importarInicialListaId) : null,
        })
      }
      navigate(`/listas-precio/${nueva.id}`)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold"><Tag className="size-5 text-primary" />Nueva lista de precios</h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader><CardTitle className="text-base">Datos de la lista</CardTitle></CardHeader>
        <CardContent>
          <Form {...form}>
            <form className="grid max-w-xl gap-4" onSubmit={form.handleSubmit(handleSubmit)}>
              <FormField
                control={form.control}
                name="nombre"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nombre</FormLabel>
                    <FormControl><Input {...field} placeholder="Ej: Lista mayorista, Precio 2, VIP…" autoFocus /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="descripcion"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Descripción <span className="font-normal text-muted-foreground">(opcional)</span></FormLabel>
                    <FormControl><Input {...field} placeholder="Ej: Precios para distribuidores con volumen" /></FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid gap-2 border-t pt-4">
                <Label>Importar precios iniciales <span className="font-normal text-muted-foreground">(opcional)</span></Label>
                <p className="text-xs text-muted-foreground">Podés partir de precios existentes y ajustarlos luego.</p>
                <RadioGroup value={importarInicial || '__ninguno__'} onValueChange={(v) => setImportarInicial(v === '__ninguno__' ? '' : v as typeof importarInicial)} className="gap-2">
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="__ninguno__" id="imp-ninguno" />
                    <Label htmlFor="imp-ninguno" className="font-normal">Empezar vacía (cargar precios manualmente)</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="venta" id="imp-venta" />
                    <Label htmlFor="imp-venta" className="font-normal">Copiar precio de venta actual de cada producto</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="costo" id="imp-costo" />
                    <Label htmlFor="imp-costo" className="font-normal">Copiar precio de costo de cada producto</Label>
                  </div>
                  {listas.length > 0 && (
                    <div className="flex items-center gap-2">
                      <RadioGroupItem value="lista" id="imp-lista" />
                      <Label htmlFor="imp-lista" className="font-normal">Copiar desde otra lista:</Label>
                    </div>
                  )}
                </RadioGroup>
                {importarInicial === 'lista' && (
                  <Select value={importarInicialListaId} onValueChange={setImportarInicialListaId}>
                    <SelectTrigger className="ml-6 w-64"><SelectValue placeholder="Elegir lista…" /></SelectTrigger>
                    <SelectContent>
                      {listas.map((l) => <SelectItem key={l.id} value={String(l.id)}>{l.nombre}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              </div>

              <div className="flex gap-2 border-t pt-4">
                <Button type="submit" disabled={saving}>{saving ? 'Creando…' : 'Crear lista'}</Button>
                <Button type="button" variant="outline" onClick={() => navigate('/listas-precio')}>Cancelar</Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}
