import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { api, ApiError, type Deposito } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { ArrowLeft, Building2, Check } from 'lucide-react'

// Misma pagina para alta y edicion, igual que el form.html viejo -- si hay
// :id en la ruta (/depositos/:id/editar) precarga el deposito existente.
export function DepositoForm() {
  const { id } = useParams<{ id: string }>()
  const editingId = id ? Number(id) : null
  const navigate = useNavigate()

  const [loadingDeposito, setLoadingDeposito] = useState(Boolean(editingId))
  const [nombre, setNombre] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [activo, setActivo] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  useEffect(() => {
    if (!editingId) return
    api.get<Deposito[]>('/api/depositos').then((all) => {
      const d = all.find((x) => x.id === editingId)
      if (!d) { setError('Depósito no encontrado.'); return }
      setNombre(d.nombre)
      setDescripcion(d.descripcion ?? '')
      setActivo(!!d.activo)
    }).catch((err) => setError(describeError(err))).finally(() => setLoadingDeposito(false))
  }, [editingId])

  async function guardar() {
    if (!nombre.trim()) return
    setSaving(true)
    setError(null)
    try {
      const d = editingId
        ? await api.put<Deposito>(`/api/depositos/${editingId}`, { nombre, descripcion, activo })
        : await api.post<Deposito>('/api/depositos', { nombre, descripcion })
      navigate(`/depositos/${d.id}`)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Building2 className="size-5 text-primary" />{editingId ? 'Editar depósito' : 'Nuevo depósito'}
        </h2>
        <Button asChild size="sm" variant="outline"><Link to="/depositos"><ArrowLeft />Volver</Link></Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loadingDeposito ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <div className="flex justify-center">
          <Card className="w-full max-w-md">
            <CardHeader><CardTitle className="text-base">{editingId ? `Editar: ${nombre}` : 'Datos del depósito'}</CardTitle></CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid gap-1.5">
                <Label>Nombre <span className="text-destructive">*</span></Label>
                <Input value={nombre} onChange={(e) => setNombre(e.target.value)} autoFocus />
              </div>
              <div className="grid gap-1.5">
                <Label>Descripción</Label>
                <Textarea
                  value={descripcion} onChange={(e) => setDescripcion(e.target.value)} rows={2}
                  placeholder="Ej: Almacén norte, Depósito de materias primas…"
                />
              </div>
              {editingId !== null && (
                <label className="flex items-center gap-2 text-sm">
                  <Switch checked={activo} onCheckedChange={setActivo} />Activo
                </label>
              )}
              <Button disabled={saving || !nombre.trim()} onClick={guardar}>
                <Check />{saving ? 'Guardando…' : 'Guardar'}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
