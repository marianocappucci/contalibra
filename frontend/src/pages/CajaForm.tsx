import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, ApiError, MEDIOS_PAGO_LABELS, type CajaConfig } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Check, Wallet } from 'lucide-react'

const TODOS_MEDIOS = Object.keys(MEDIOS_PAGO_LABELS)

// Misma pagina para alta y edicion, igual que el form.html viejo -- si hay
// :id en la ruta (/cajas/:id/editar) precarga la caja existente.
export function CajaForm() {
  const { id } = useParams<{ id: string }>()
  const editingId = id ? Number(id) : null
  const navigate = useNavigate()

  const [loadingCaja, setLoadingCaja] = useState(Boolean(editingId))
  const [nombre, setNombre] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [mediosPago, setMediosPago] = useState<string[]>([])
  const [activo, setActivo] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!editingId) {
      setMediosPago([])
      return
    }
    api.get<CajaConfig[]>('/api/cajas').then((cajas) => {
      const c = cajas.find((x) => x.id === editingId)
      if (!c) { setError('Caja no encontrada.'); return }
      setNombre(c.nombre)
      setDescripcion(c.descripcion ?? '')
      setMediosPago(c.medios_pago)
      setActivo(!!c.activo)
    }).catch((err) => setError(describeError(err))).finally(() => setLoadingCaja(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editingId])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  function toggleMedio(medio: string) {
    setMediosPago((m) => m.includes(medio) ? m.filter((x) => x !== medio) : [...m, medio])
  }

  async function guardar() {
    if (!nombre.trim()) return
    setSaving(true)
    setError(null)
    try {
      const payload = { nombre, descripcion, medios_pago: mediosPago, activo }
      if (editingId) {
        await api.put(`/api/cajas/${editingId}`, payload)
      } else {
        await api.post('/api/cajas', payload)
      }
      navigate('/cajas')
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <Wallet className="size-5 text-primary" />{editingId ? 'Editar caja' : 'Nueva caja'}
      </h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loadingCaja ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <Card>
          <CardHeader><CardTitle className="text-base">Datos de la caja</CardTitle></CardHeader>
          <CardContent className="grid gap-3">
            <div className="flex flex-wrap items-end gap-3">
              <div className="grid gap-1.5"><Label>Nombre</Label><Input value={nombre} onChange={(e) => setNombre(e.target.value)} className="w-48" placeholder="Ej: Caja mostrador, Caja online…" /></div>
              <div className="grid gap-1.5"><Label>Descripción</Label><Input value={descripcion} onChange={(e) => setDescripcion(e.target.value)} className="w-64" /></div>
            </div>
            <div className="grid gap-1.5">
              <Label>Medios de pago habilitados</Label>
              <div className="flex flex-wrap gap-3">
                {TODOS_MEDIOS.map((m) => (
                  <label key={m} className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={mediosPago.includes(m)} onChange={() => toggleMedio(m)} />
                    {MEDIOS_PAGO_LABELS[m]}
                  </label>
                ))}
              </div>
            </div>
            {editingId !== null && (
              <label className="flex w-fit items-center gap-2 text-sm">
                <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
                Activa
              </label>
            )}
            <div className="flex gap-2">
              <Button disabled={saving || !nombre.trim()} onClick={guardar}><Check />{saving ? 'Guardando…' : editingId ? 'Guardar cambios' : 'Crear caja'}</Button>
              <Button type="button" variant="outline" onClick={() => navigate('/cajas')}>Cancelar</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
