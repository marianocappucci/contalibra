import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { api, ApiError, type Presupuesto } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Send, XCircle, CheckCircle2, RefreshCw, Receipt, CheckCheck, Undo2, Mail, Trash2, ArrowLeft,
} from 'lucide-react'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

const estadoVariant: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  aceptado: 'default', enviado: 'secondary', borrador: 'outline', rechazado: 'destructive', vencido: 'destructive', facturado: 'default',
}

const ESTADO_LABELS: Record<string, string> = {
  borrador: 'Borrador', enviado: 'Enviado', pendiente: 'Enviado', aceptado: 'Aceptado',
  rechazado: 'Rechazado', vencido: 'Vencido', facturado: 'Facturado',
}

export function PresupuestoDetalle() {
  const { id } = useParams<{ id: string }>()
  const presId = Number(id)
  const navigate = useNavigate()

  const [p, setP] = useState<Presupuesto | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [emailTo, setEmailTo] = useState('')

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presId])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function cargar() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<Presupuesto>(`/api/presupuestos/${presId}`)
      setP(data)
      setEmailTo(data.client_email || '')
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function cambiarEstado(estado: string, convertirRemito = false) {
    setError(null)
    try {
      await api.post(`/api/presupuestos/${presId}/estado`, { estado, convertir_remito: convertirRemito })
      await cargar()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function enviarEmail() {
    if (!emailTo.trim()) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/presupuestos/${presId}/enviar-email`, { email: emailTo })
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function eliminar() {
    if (!window.confirm('¿Eliminar este presupuesto?')) return
    setError(null)
    try {
      await api.del(`/api/presupuestos/${presId}`)
      navigate('/presupuestos')
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{p ? `${p.number} — ${p.client_name}` : 'Presupuesto'}</h2>
        <Button asChild size="sm" variant="outline"><Link to="/presupuestos"><ArrowLeft />Volver</Link></Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading || !p ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        (() => {
          const st = p.status
          return (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader><CardTitle className="text-base">Datos del cliente</CardTitle></CardHeader>
                  <CardContent className="grid gap-1.5 text-sm">
                    <p><span className="text-muted-foreground">Cliente:</span> {p.client_name}</p>
                    {p.client_cuit && <p><span className="text-muted-foreground">CUIT / DNI:</span> {p.client_cuit}</p>}
                    {p.client_address && <p><span className="text-muted-foreground">Domicilio:</span> {p.client_address}</p>}
                    {p.client_email && <p><span className="text-muted-foreground">Email:</span> {p.client_email}</p>}
                    {p.client_phone && <p><span className="text-muted-foreground">Teléfono:</span> {p.client_phone}</p>}
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader><CardTitle className="text-base">Datos del presupuesto</CardTitle></CardHeader>
                  <CardContent className="grid gap-1.5 text-sm">
                    <p><span className="text-muted-foreground">Número:</span> <span className="font-mono">{p.number}</span></p>
                    <p><span className="text-muted-foreground">Fecha:</span> {p.date}</p>
                    <p><span className="text-muted-foreground">Válido hasta:</span> {p.valid_until || '—'}</p>
                    <p><span className="text-muted-foreground">Estado:</span> <Badge variant={estadoVariant[st] ?? 'outline'}>{ESTADO_LABELS[st] ?? st}</Badge></p>
                    {p.observations && <p><span className="text-muted-foreground">Observaciones:</span> {p.observations}</p>}
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader><CardTitle className="text-base">Ítems</CardTitle></CardHeader>
                <CardContent className="p-0">
                  <table className="w-full text-sm">
                    <thead className="border-b text-muted-foreground">
                      <tr>
                        <th className="p-3 text-left font-medium">Descripción</th>
                        <th className="p-3 text-right font-medium">Cantidad</th>
                        <th className="p-3 text-right font-medium">Precio unit.</th>
                        <th className="p-3 text-right font-medium">Subtotal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.items.map((it, i) => (
                        <tr key={i} className="border-b last:border-0">
                          <td className="whitespace-pre-line p-3">{it.description}</td>
                          <td className="p-3 text-right">{it.qty}</td>
                          <td className="p-3 text-right">{formatCurrency(it.unit_price)}</td>
                          <td className="p-3 text-right">{formatCurrency(it.subtotal)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="font-medium">
                      <tr><td colSpan={3} className="p-3 text-right text-muted-foreground">Subtotal</td><td className="p-3 text-right">{formatCurrency(p.subtotal)}</td></tr>
                      <tr><td colSpan={3} className="p-3 text-right text-muted-foreground">IVA {Math.round(p.tax_rate * 100)}%</td><td className="p-3 text-right">{formatCurrency(p.tax_amount)}</td></tr>
                      <tr className="text-base"><td colSpan={3} className="p-3 text-right font-semibold">TOTAL</td><td className="p-3 text-right font-semibold text-primary">{formatCurrency(p.total)}</td></tr>
                    </tfoot>
                  </table>
                </CardContent>
              </Card>

              {st !== 'facturado' && (
                <Card>
                  <CardHeader><CardTitle className="text-base">Acciones</CardTitle></CardHeader>
                  <CardContent className="flex flex-wrap gap-2">
                    {st === 'borrador' && (
                      <>
                        <Button size="sm" onClick={() => cambiarEstado('enviado')}><Send />Marcar como enviado</Button>
                        <Button size="sm" variant="outline" onClick={() => cambiarEstado('rechazado')}><XCircle />Rechazar</Button>
                      </>
                    )}
                    {st === 'enviado' && (
                      <>
                        <Button size="sm" onClick={() => cambiarEstado('aceptado', false)}><CheckCircle2 />Aceptar</Button>
                        <Button size="sm" variant="outline" onClick={() => cambiarEstado('aceptado', true)}><RefreshCw />Aceptar y convertir a remito</Button>
                        <Button size="sm" variant="outline" onClick={() => cambiarEstado('rechazado')}><XCircle />Rechazar</Button>
                      </>
                    )}
                    {st === 'aceptado' && (
                      <>
                        <Button asChild size="sm"><Link to="/facturas/nueva"><Receipt />Generar factura</Link></Button>
                        <Button size="sm" variant="outline" onClick={() => cambiarEstado('facturado')}><CheckCheck />Marcar como facturado</Button>
                        <Button size="sm" variant="outline" onClick={() => cambiarEstado('rechazado')}><XCircle />Rechazar</Button>
                      </>
                    )}
                    {(st === 'rechazado' || st === 'vencido') && (
                      <Button size="sm" variant="outline" onClick={() => cambiarEstado('borrador')}><Undo2 />Reactivar como borrador</Button>
                    )}
                    {st === 'borrador' && (
                      <Button size="sm" variant="outline" onClick={eliminar}><Trash2 />Eliminar presupuesto</Button>
                    )}
                  </CardContent>
                </Card>
              )}

              {st === 'facturado' && (
                <p className="flex items-center gap-2 rounded-md border bg-muted/50 p-3 text-sm">
                  <CheckCheck className="size-4 shrink-0" />Este presupuesto está <strong>facturado</strong> y cerrado comercialmente.
                </p>
              )}

              <Card>
                <CardHeader><CardTitle className="text-base">Enviar por email</CardTitle></CardHeader>
                <CardContent className="flex flex-wrap items-end gap-3">
                  <div className="grid gap-1.5"><Label>Destinatario</Label><Input type="email" value={emailTo} onChange={(e) => setEmailTo(e.target.value)} className="w-56" placeholder="email@ejemplo.com" /></div>
                  <Button size="sm" variant="outline" disabled={saving || !emailTo.trim()} onClick={enviarEmail}><Mail />Enviar</Button>
                </CardContent>
              </Card>
            </>
          )
        })()
      )}
    </div>
  )
}
