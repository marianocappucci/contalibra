import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError, type Turno } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PlayCircle } from 'lucide-react'

export function TurnoAbrir() {
  const navigate = useNavigate()
  const [montoInicial, setMontoInicial] = useState('0')
  const [notas, setNotas] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function abrir() {
    setSaving(true)
    setError(null)
    try {
      const turno = await api.post<Turno>('/api/turnos/abrir', { monto_inicial: Number(montoInicial) || 0, notas })
      navigate(`/turnos/${turno.id}`)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold"><PlayCircle className="size-5 text-emerald-600" />Abrir turno</h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card className="max-w-md">
        <CardHeader>
          <CardTitle className="text-base">Datos de apertura</CardTitle>
          <CardDescription>Registrá el efectivo en caja al inicio del turno. Se usa para calcular la diferencia al cierre.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid gap-1.5"><Label>Fondo inicial</Label><Input type="number" step="0.01" value={montoInicial} onChange={(e) => setMontoInicial(e.target.value)} /></div>
          <div className="grid gap-1.5"><Label>Notas</Label><Input value={notas} onChange={(e) => setNotas(e.target.value)} placeholder="Ej: Turno mañana, cajero Juan…" /></div>
          <div className="flex gap-2 pt-1">
            <Button disabled={saving} onClick={abrir}><PlayCircle />{saving ? 'Abriendo…' : 'Abrir turno ahora'}</Button>
            <Button type="button" variant="outline" onClick={() => navigate('/turnos')}>Cancelar</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
