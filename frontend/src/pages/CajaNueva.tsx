import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, ApiError, MEDIOS_PAGO_LABELS, type CajaConfig } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { ArrowDownCircle, ArrowUpCircle, Check, PiggyBank } from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

export function CajaNueva() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const facturaId = searchParams.get('factura_id')

  const [cajas, setCajas] = useState<CajaConfig[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [tipo, setTipo] = useState('ingreso')
  const [fecha, setFecha] = useState(todayIso())
  const [concepto, setConcepto] = useState('')
  const [monto, setMonto] = useState('')
  const [referencia, setReferencia] = useState('')
  const [cajaId, setCajaId] = useState('')
  const [medioPago, setMedioPago] = useState('efectivo')

  useEffect(() => {
    api.get<CajaConfig[]>('/api/cajas').then((data) => {
      setCajas(data)
      const def = data.find((c) => c.es_default) ?? data[0]
      if (def) setCajaId(String(def.id))
    }).catch(() => {})
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function crear() {
    if (!concepto.trim() || !monto) return
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/caja', {
        fecha, tipo, concepto, monto: Number(monto), referencia,
        caja_id: cajaId ? Number(cajaId) : null, medio_pago: medioPago,
        factura_id: facturaId ? Number(facturaId) : null,
      })
      navigate(facturaId ? `/facturas/${facturaId}` : '/caja')
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold"><PiggyBank className="size-5 text-primary" />Nuevo movimiento de caja</h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader><CardTitle className="text-base">Datos del movimiento</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="grid gap-1.5">
            <Label>Tipo</Label>
            <Select value={tipo} onValueChange={setTipo}>
              <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ingreso"><ArrowDownCircle />Ingreso</SelectItem>
                <SelectItem value="egreso"><ArrowUpCircle />Egreso</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5"><Label>Fecha</Label><Input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="w-40" /></div>
          <div className="grid gap-1.5"><Label>Concepto</Label><Input value={concepto} onChange={(e) => setConcepto(e.target.value)} className="w-52" placeholder="Ej: Cobro factura cliente / Pago servicios" /></div>
          <div className="grid gap-1.5"><Label>Monto</Label><Input type="number" step="0.01" value={monto} onChange={(e) => setMonto(e.target.value)} className="w-32" /></div>
          <div className="grid gap-1.5"><Label>Referencia</Label><Input value={referencia} onChange={(e) => setReferencia(e.target.value)} className="w-40" placeholder="Opcional — N° factura, proveedor, etc." /></div>
          {cajas.length > 1 && (
            <div className="grid gap-1.5">
              <Label>Caja</Label>
              <Select value={cajaId} onValueChange={setCajaId}>
                <SelectTrigger className="w-36"><SelectValue placeholder="Por defecto" /></SelectTrigger>
                <SelectContent>
                  {cajas.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="grid gap-1.5">
            <Label>Medio de pago</Label>
            <Select value={medioPago} onValueChange={setMedioPago}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(MEDIOS_PAGO_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <Button disabled={saving || !concepto.trim() || !monto} onClick={crear}><Check />{saving ? 'Guardando…' : 'Guardar movimiento'}</Button>
          <Button type="button" variant="outline" onClick={() => navigate(facturaId ? `/facturas/${facturaId}` : '/caja')}>Cancelar</Button>
        </CardContent>
      </Card>
    </div>
  )
}
