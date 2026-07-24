import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { api, ApiError, TIPOS_CUENTA_TESORERIA, type CuentaTesoreria } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { ArrowLeft, Archive, Check, Landmark } from 'lucide-react'

const EMPTY_FORM = { nombre: '', tipo: 'banco', banco: '', numero: '', descripcion: '', saldo_inicial: '0' }

// Misma pagina para alta y edicion, igual que el cuenta_form.html viejo -- si
// hay :id en la ruta (/tesoreria/:id/editar) precarga la cuenta existente.
export function TesoreriaCuentaForm() {
  const { id } = useParams<{ id: string }>()
  const editingId = id ? Number(id) : null
  const navigate = useNavigate()

  const [loadingCuenta, setLoadingCuenta] = useState(Boolean(editingId))
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  useEffect(() => {
    if (!editingId) return
    api.get<{ cuenta: CuentaTesoreria }>(`/api/tesoreria/cuentas/${editingId}`).then(({ cuenta }) => {
      setForm({
        nombre: cuenta.nombre, tipo: cuenta.tipo, banco: cuenta.banco ?? '', numero: cuenta.numero ?? '',
        descripcion: cuenta.descripcion ?? '', saldo_inicial: String(cuenta.saldo_inicial),
      })
    }).catch((err) => setError(describeError(err))).finally(() => setLoadingCuenta(false))
  }, [editingId])

  async function guardar() {
    if (!form.nombre.trim()) return
    setSaving(true)
    setError(null)
    try {
      const payload = { ...form, saldo_inicial: Number(form.saldo_inicial) || 0 }
      const c = editingId
        ? await api.put<CuentaTesoreria>(`/api/tesoreria/cuentas/${editingId}`, payload)
        : await api.post<CuentaTesoreria>('/api/tesoreria/cuentas', payload)
      navigate(`/tesoreria/${c.id}`)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function archivar() {
    if (!editingId) return
    if (!window.confirm('¿Archivar esta cuenta? Los movimientos se conservan.')) return
    setError(null)
    try {
      await api.del(`/api/tesoreria/cuentas/${editingId}`)
      navigate('/tesoreria')
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Landmark className="size-5 text-primary" />{editingId ? 'Editar cuenta' : 'Nueva cuenta'}
        </h2>
        <Button asChild size="sm" variant="outline"><Link to="/tesoreria"><ArrowLeft />Volver</Link></Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loadingCuenta ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <div className="flex justify-center">
          <div className="grid w-full max-w-xl gap-3">
            <Card>
              <CardHeader><CardTitle className="text-base">Datos de la cuenta</CardTitle></CardHeader>
              <CardContent className="grid gap-4">
                <div className="grid gap-1.5">
                  <Label>Nombre <span className="text-destructive">*</span></Label>
                  <Input
                    value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} autoFocus
                    placeholder="Ej: Banco Galicia Cta. Cte., Caja chica, MercadoPago…"
                  />
                </div>
                <div className="grid gap-1.5">
                  <Label>Tipo</Label>
                  <Select value={form.tipo} onValueChange={(v) => setForm({ ...form, tipo: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {TIPOS_CUENTA_TESORERIA.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                {form.tipo !== 'efectivo' && (
                  <div className="grid grid-cols-2 gap-3">
                    <div className="grid gap-1.5"><Label>Banco / Entidad</Label><Input value={form.banco} onChange={(e) => setForm({ ...form, banco: e.target.value })} placeholder="Ej: Galicia, BBVA, MP…" /></div>
                    <div className="grid gap-1.5"><Label>N° de cuenta / CBU / alias</Label><Input value={form.numero} onChange={(e) => setForm({ ...form, numero: e.target.value })} placeholder="Últimos 4 dígitos o alias" /></div>
                  </div>
                )}
                <div className="grid gap-1.5">
                  <Label>Saldo inicial</Label>
                  <Input type="number" step="0.01" value={form.saldo_inicial} onChange={(e) => setForm({ ...form, saldo_inicial: e.target.value })} placeholder="0.00" />
                  <p className="text-xs text-muted-foreground">Saldo al momento de dar de alta la cuenta en el sistema.</p>
                </div>
                <div className="grid gap-1.5">
                  <Label>Descripción <span className="font-normal text-muted-foreground">(opcional)</span></Label>
                  <Input value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} placeholder="Nota interna sobre esta cuenta" />
                </div>
                <div className="flex justify-end gap-2">
                  <Button asChild variant="outline"><Link to="/tesoreria">Cancelar</Link></Button>
                  <Button disabled={saving || !form.nombre.trim()} onClick={guardar}>
                    <Check />{saving ? 'Guardando…' : editingId ? 'Guardar cambios' : 'Crear cuenta'}
                  </Button>
                </div>
              </CardContent>
            </Card>
            {editingId !== null && (
              <div className="flex justify-end">
                <Button size="sm" variant="outline" className="text-destructive hover:text-destructive" onClick={archivar}>
                  <Archive />Archivar cuenta
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
