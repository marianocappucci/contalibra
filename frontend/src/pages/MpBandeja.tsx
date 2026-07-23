import { useEffect, useState } from 'react'
import { api, ApiError, IVA_CONDITIONS, type MpMovimiento, type MpPago } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

type Bandeja = {
  pendientes: MpPago[]
  historial: MpPago[]
  transferencias: MpMovimiento[]
  transferencias_hist: MpMovimiento[]
  mp_concepto_default: string
}

export function MpBandeja() {
  const [data, setData] = useState<Bandeja | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [tab, setTab] = useState<'pagos' | 'transferencias'>('pagos')

  const [creandoCliente, setCreandoCliente] = useState<{ kind: 'pago' | 'mov'; id: number } | null>(null)
  const [nombre, setNombre] = useState('')
  const [email, setEmail] = useState('')
  const [cuit, setCuit] = useState('')
  const [ivaCond, setIvaCond] = useState('Consumidor Final')
  const [saving, setSaving] = useState(false)

  useEffect(() => { load() }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setData(await api.get<Bandeja>('/api/mp-bandeja'))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function sincronizar() {
    setSyncing(true)
    setError(null)
    setMsg(null)
    try {
      const res = await api.post<{ nuevos: number }>('/api/mp-bandeja/sincronizar', { dias: 7 })
      setMsg(`Sincronizado: ${res.nuevos} movimiento(s) nuevo(s).`)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSyncing(false)
    }
  }

  async function ignorar(kind: 'pago' | 'mov', id: number) {
    setError(null)
    try {
      await api.post(`/api/mp-bandeja/${kind === 'pago' ? 'pagos' : 'movimientos'}/${id}/ignorar`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  function abrirCrearCliente(kind: 'pago' | 'mov', item: MpPago | MpMovimiento) {
    setCreandoCliente({ kind, id: item.id })
    setNombre(item.payer_name || ''); setEmail(item.payer_email || '')
    setCuit(item.payer_id_number || ''); setIvaCond('Consumidor Final')
  }

  async function crearCliente() {
    if (!creandoCliente || !nombre.trim()) return
    setSaving(true)
    setError(null)
    try {
      const path = creandoCliente.kind === 'pago' ? 'pagos' : 'movimientos'
      await api.post(`/api/mp-bandeja/${path}/${creandoCliente.id}/crear-cliente`, {
        nombre, email, cuit_dni: cuit, iva_condition: ivaCond,
      })
      setCreandoCliente(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function facturar(kind: 'pago' | 'mov', id: number) {
    setSaving(true)
    setError(null)
    setMsg(null)
    try {
      const path = kind === 'pago' ? 'pagos' : 'movimientos'
      const res = await api.post<{ numero: string; tipo_label: string; email_sent: boolean }>(`/api/mp-bandeja/${path}/${id}/facturar`, {})
      setMsg(`Facturado: ${res.tipo_label} ${res.numero}${res.email_sent ? ' — email enviado' : ''}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  const pendientesPagos = data?.pendientes ?? []
  const historialPagos = data?.historial ?? []
  const pendientesMov = data?.transferencias ?? []
  const historialMov = data?.transferencias_hist ?? []

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Bandeja MercadoPago</h2>
        <Button disabled={syncing} onClick={sincronizar}>{syncing ? 'Sincronizando…' : 'Sincronizar (últimos 7 días)'}</Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-emerald-600 dark:text-emerald-400">{msg}</p>}

      <div className="flex gap-1 border-b pb-2">
        <Button size="sm" variant={tab === 'pagos' ? 'default' : 'ghost'} onClick={() => setTab('pagos')}>Pagos ({pendientesPagos.length})</Button>
        <Button size="sm" variant={tab === 'transferencias' ? 'default' : 'ghost'} onClick={() => setTab('transferencias')}>Transferencias ({pendientesMov.length})</Button>
      </div>

      {creandoCliente && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nuevo cliente desde pago</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5"><Label>Nombre</Label><Input value={nombre} onChange={(e) => setNombre(e.target.value)} className="w-48" /></div>
            <div className="grid gap-1.5"><Label>Email</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-52" /></div>
            <div className="grid gap-1.5"><Label>CUIT/DNI</Label><Input value={cuit} onChange={(e) => setCuit(e.target.value)} className="w-36" /></div>
            <div className="grid gap-1.5">
              <Label>Condición IVA</Label>
              <Select value={ivaCond} onValueChange={setIvaCond}>
                <SelectTrigger className="w-52"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {IVA_CONDITIONS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button disabled={saving} onClick={crearCliente}>{saving ? 'Guardando…' : 'Crear cliente'}</Button>
            <Button type="button" variant="outline" onClick={() => setCreandoCliente(null)}>Cancelar</Button>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : tab === 'pagos' ? (
        <>
          <Card>
            <CardHeader><CardTitle className="text-base">Pendientes de facturar</CardTitle></CardHeader>
            <CardContent>
              {pendientesPagos.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Sin pagos pendientes.</p>
              ) : (
                <ul className="divide-y">
                  {pendientesPagos.map((p) => (
                    <li key={p.id} className="grid gap-2 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="font-medium">{formatCurrency(p.monto)} — {p.payer_name || p.payer_email || 'Sin datos'}</p>
                          <p className="text-sm text-muted-foreground">
                            {p.cliente ? `Cliente: ${p.cliente.name}` : 'Sin cliente asociado'} · MP#{p.mp_payment_id}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          {!p.cliente && <Button size="sm" variant="outline" onClick={() => abrirCrearCliente('pago', p)}>Crear cliente</Button>}
                          <Button size="sm" variant="outline" disabled={saving} onClick={() => facturar('pago', p.id)}>Facturar</Button>
                          <Button size="sm" variant="ghost" onClick={() => ignorar('pago', p.id)}>Ignorar</Button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-base">Historial</CardTitle></CardHeader>
            <CardContent>
              {historialPagos.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Sin historial todavía.</p>
              ) : (
                <ul className="divide-y">
                  {historialPagos.map((p) => (
                    <li key={p.id} className="flex items-center justify-between py-2 text-sm">
                      <span>{formatCurrency(p.monto)} — {p.payer_name || p.payer_email}</span>
                      <Badge variant={p.estado_factura === 'facturado' ? 'default' : 'outline'}>{p.estado_factura}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      ) : (
        <>
          <Card>
            <CardHeader><CardTitle className="text-base">Transferencias pendientes</CardTitle></CardHeader>
            <CardContent>
              {pendientesMov.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Sin transferencias pendientes.</p>
              ) : (
                <ul className="divide-y">
                  {pendientesMov.map((m) => (
                    <li key={m.id} className="grid gap-2 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="font-medium">{formatCurrency(m.monto)} — {m.origen_nombre || m.payer_name || 'Sin datos'} ({m.fecha})</p>
                          <p className="text-sm text-muted-foreground">
                            {m.cliente ? `Cliente: ${m.cliente.name}` : 'Sin cliente asociado'} · {m.descripcion || m.mp_movement_id}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          {!m.cliente && <Button size="sm" variant="outline" onClick={() => abrirCrearCliente('mov', m)}>Crear cliente</Button>}
                          <Button size="sm" variant="outline" disabled={saving} onClick={() => facturar('mov', m.id)}>Facturar</Button>
                          <Button size="sm" variant="ghost" onClick={() => ignorar('mov', m.id)}>Ignorar</Button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="text-base">Historial</CardTitle></CardHeader>
            <CardContent>
              {historialMov.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Sin historial todavía.</p>
              ) : (
                <ul className="divide-y">
                  {historialMov.map((m) => (
                    <li key={m.id} className="flex items-center justify-between py-2 text-sm">
                      <span>{formatCurrency(m.monto)} — {m.origen_nombre || m.payer_name} ({m.fecha})</span>
                      <Badge variant={m.estado_factura === 'facturado' ? 'default' : 'outline'}>{m.estado_factura}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
