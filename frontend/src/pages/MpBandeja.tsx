import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, IVA_CONDITIONS, type MpMovimiento, type MpPago } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  CreditCard, Wallet, Landmark, Banknote, RefreshCw, UserPlus, ReceiptText, X, Mail,
  Forward, UserRoundX, MailWarning,
} from 'lucide-react'

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

function OrigenBadge({ tipo, metodo }: { tipo: string | null; metodo?: string | null }) {
  if (!tipo) return <span className="text-muted-foreground">—</span>
  const t = tipo.toLowerCase()
  const map: Record<string, { label: string; icon: typeof Wallet; className: string }> = {
    account_money: { label: 'Cuenta MP', icon: Wallet, className: 'bg-sky-500 text-white' },
    credit_card: { label: 'Tarjeta de crédito', icon: CreditCard, className: 'bg-emerald-600 text-white' },
    debit_card: { label: 'Tarjeta de débito', icon: CreditCard, className: 'bg-cyan-600 text-white' },
    ticket: { label: 'Efectivo', icon: Banknote, className: 'bg-amber-500 text-white' },
    bank_transfer: { label: 'Transf. bancaria', icon: Landmark, className: 'bg-secondary text-secondary-foreground' },
  }
  const conf = map[t] ?? { label: tipo, icon: CreditCard, className: 'bg-muted text-foreground' }
  const Icon = conf.icon
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${conf.className}`}>
      <Icon className="size-3.5" />{conf.label}{metodo && metodo !== 'mercadopago' ? ` (${metodo.toUpperCase()})` : ''}
    </span>
  )
}

export function MpBandeja() {
  const [data, setData] = useState<Bandeja | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [dias, setDias] = useState('7')
  const [tab, setTab] = useState<'pagos' | 'transferencias'>('pagos')

  const [creandoCliente, setCreandoCliente] = useState<{ kind: 'pago' | 'mov'; id: number } | null>(null)
  const [nombre, setNombre] = useState('')
  const [email, setEmail] = useState('')
  const [tipoId, setTipoId] = useState('DNI')
  const [cuit, setCuit] = useState('')
  const [direccion, setDireccion] = useState('')
  const [ivaCond, setIvaCond] = useState('Consumidor Final')
  const [saving, setSaving] = useState(false)

  const [cargandoEmail, setCargandoEmail] = useState<number | null>(null)
  const [emailMov, setEmailMov] = useState('')
  const [nombreMov, setNombreMov] = useState('')

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
      const res = await api.post<{ nuevos: number }>('/api/mp-bandeja/sincronizar', { dias: Number(dias) })
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
    setTipoId(item.payer_id_type || 'DNI'); setCuit(item.payer_id_number || '')
    setDireccion(''); setIvaCond('Consumidor Final')
  }

  async function crearCliente() {
    if (!creandoCliente || !nombre.trim()) return
    setSaving(true)
    setError(null)
    try {
      const path = creandoCliente.kind === 'pago' ? 'pagos' : 'movimientos'
      await api.post(`/api/mp-bandeja/${path}/${creandoCliente.id}/crear-cliente`, {
        nombre, email, cuit_dni: cuit, iva_condition: ivaCond, address: direccion,
      })
      setCreandoCliente(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  function abrirCargarEmail(m: MpMovimiento) {
    setCargandoEmail(m.id)
    setEmailMov(m.payer_email || '')
    setNombreMov(m.payer_name || m.origen_nombre || '')
  }

  async function guardarEmailMov() {
    if (cargandoEmail === null || !emailMov.trim()) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/mp-bandeja/movimientos/${cargandoEmail}/guardar-datos`, {
        payer_email: emailMov.trim(), payer_name: nombreMov.trim(),
      })
      setCargandoEmail(null)
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

  async function reenviarEmail(facturaId: number) {
    setSaving(true)
    setError(null)
    setMsg(null)
    try {
      await api.post(`/api/mp-bandeja/facturas/${facturaId}/reenviar`, {})
      setMsg('Email reenviado correctamente.')
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

  const columnsHistorialPagos = useMemo<ColumnDef<MpPago>[]>(() => [
    { accessorKey: 'created_at', header: sortableHeader('Fecha') },
    { id: 'origen', header: 'Tipo', cell: ({ row }) => <OrigenBadge tipo={row.original.payment_type} metodo={row.original.payment_method} /> },
    { id: 'pagador', header: 'Pagador', cell: ({ row }) => row.original.payer_name || row.original.payer_email || '—' },
    { id: 'cliente', header: 'Cliente', cell: ({ row }) => row.original.cliente ? row.original.cliente.name : <span className="text-muted-foreground">—</span> },
    { accessorKey: 'monto', header: 'Monto', cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.monto)}</span> },
    { id: 'estado', header: 'Estado', cell: ({ row }) => <Badge variant={row.original.estado_factura === 'facturado' ? 'default' : 'outline'}>{row.original.estado_factura === 'facturado' ? 'Facturado' : 'Ignorado'}</Badge> },
    {
      id: 'factura',
      header: 'Factura',
      cell: ({ row }) => row.original.factura_id ? (
        <div className="flex items-center gap-1">
          <Button asChild size="sm" variant="outline"><a href={`/facturas?ver=${row.original.factura_id}`}><ReceiptText />Ver</a></Button>
          {row.original.cliente?.email
            ? <Button size="icon" variant="outline" title="Reenviar email" disabled={saving} onClick={() => reenviarEmail(row.original.factura_id!)}><Forward className="size-4" /></Button>
            : <Badge variant="outline" className="text-amber-700 dark:text-amber-400"><MailWarning className="mr-1 size-3.5" />Sin email</Badge>}
        </div>
      ) : <span className="text-muted-foreground">—</span>,
    },
  ], [saving])

  const columnsHistorialMov = useMemo<ColumnDef<MpMovimiento>[]>(() => [
    { id: 'fecha', header: sortableHeader('Fecha'), accessorFn: (r) => r.fecha || r.created_at },
    { id: 'origen', header: 'Tipo', cell: ({ row }) => <OrigenBadge tipo={row.original.tipo} metodo={row.original.origen_banco} /> },
    { id: 'origen_nombre', header: 'Emisor', cell: ({ row }) => row.original.origen_nombre || row.original.payer_name || '—' },
    { id: 'cliente', header: 'Cliente', cell: ({ row }) => row.original.cliente ? row.original.cliente.name : <span className="text-muted-foreground">—</span> },
    { accessorKey: 'monto', header: 'Monto', cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.monto)}</span> },
    { id: 'estado', header: 'Estado', cell: ({ row }) => <Badge variant={row.original.estado_factura === 'facturado' ? 'default' : 'outline'}>{row.original.estado_factura === 'facturado' ? 'Facturado' : 'Ignorado'}</Badge> },
    {
      id: 'factura',
      header: 'Factura',
      cell: ({ row }) => row.original.factura_id ? (
        <div className="flex items-center gap-1">
          <Button asChild size="sm" variant="outline"><a href={`/facturas?ver=${row.original.factura_id}`}><ReceiptText />Ver</a></Button>
          <Button size="icon" variant="outline" title="Reenviar email" disabled={saving} onClick={() => reenviarEmail(row.original.factura_id!)}><Forward className="size-4" /></Button>
        </div>
      ) : <span className="text-muted-foreground">—</span>,
    },
  ], [saving])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><CreditCard className="size-5 text-sky-500" />Bandeja MercadoPago</h2>
        <div className="flex items-end gap-2">
          <div className="grid gap-1.5">
            <Label>Sincronizar</Label>
            <Select value={dias} onValueChange={setDias}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Últimos 7 días</SelectItem>
                <SelectItem value="15">Últimos 15 días</SelectItem>
                <SelectItem value="30">Últimos 30 días</SelectItem>
                <SelectItem value="60">Últimos 60 días</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button disabled={syncing} onClick={sincronizar}><RefreshCw />{syncing ? 'Sincronizando…' : 'Sincronizar'}</Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-emerald-600 dark:text-emerald-400">{msg}</p>}

      <div className="flex gap-1 border-b pb-2">
        <Button size="sm" variant={tab === 'pagos' ? 'default' : 'ghost'} onClick={() => setTab('pagos')}>Pagos ({pendientesPagos.length})</Button>
        <Button size="sm" variant={tab === 'transferencias' ? 'default' : 'ghost'} onClick={() => setTab('transferencias')}>Transferencias ({pendientesMov.length})</Button>
      </div>

      {creandoCliente && (
        <Card>
          <CardHeader><CardTitle className="text-base">Dar de alta cliente</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5"><Label>Nombre / Razón social *</Label><Input value={nombre} onChange={(e) => setNombre(e.target.value)} className="w-48" /></div>
            <div className="grid gap-1.5"><Label>Email</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-52" placeholder="Para enviar la factura" /></div>
            <div className="grid gap-1.5"><Label>Tipo ID</Label><Input value={tipoId} onChange={(e) => setTipoId(e.target.value)} className="w-24" placeholder="DNI / CUIT" /></div>
            <div className="grid gap-1.5"><Label>CUIT/DNI</Label><Input value={cuit} onChange={(e) => setCuit(e.target.value)} className="w-36" /></div>
            <div className="grid gap-1.5"><Label>Domicilio</Label><Input value={direccion} onChange={(e) => setDireccion(e.target.value)} className="w-48" placeholder="Opcional" /></div>
            <div className="grid gap-1.5">
              <Label>Condición IVA</Label>
              <Select value={ivaCond} onValueChange={setIvaCond}>
                <SelectTrigger className="w-52"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {IVA_CONDITIONS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button disabled={saving || !nombre.trim()} onClick={crearCliente}><UserPlus />{saving ? 'Guardando…' : 'Dar de alta'}</Button>
            <Button type="button" variant="outline" onClick={() => setCreandoCliente(null)}>Cancelar</Button>
          </CardContent>
        </Card>
      )}

      {cargandoEmail !== null && (
        <Card>
          <CardHeader><CardTitle className="text-base">Datos del emisor</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5"><Label>Nombre completo</Label><Input value={nombreMov} onChange={(e) => setNombreMov(e.target.value)} className="w-52" /></div>
            <div className="grid gap-1.5"><Label>Email *</Label><Input type="email" value={emailMov} onChange={(e) => setEmailMov(e.target.value)} className="w-52" placeholder="email@ejemplo.com" /></div>
            <Button disabled={saving || !emailMov.trim()} onClick={guardarEmailMov}><Mail />{saving ? 'Guardando…' : 'Guardar'}</Button>
            <Button type="button" variant="outline" onClick={() => setCargandoEmail(null)}>Cancelar</Button>
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
                        <div className="grid gap-1">
                          <p className="font-medium">{formatCurrency(p.monto)} — {p.payer_name || p.payer_email || 'Sin datos'}</p>
                          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                            <OrigenBadge tipo={p.payment_type} metodo={p.payment_method} />
                            {p.cliente
                              ? <span>Cliente: {p.cliente.name}{!p.cliente.email && <Badge variant="outline" className="ml-1 text-amber-700 dark:text-amber-400"><MailWarning className="mr-1 size-3.5" />Sin email</Badge>}</span>
                              : <span className="flex items-center gap-1"><UserRoundX className="size-3.5" />Sin registro</span>}
                            <span>· MP#{p.mp_payment_id}</span>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          {!p.cliente && <Button size="sm" variant="outline" onClick={() => abrirCrearCliente('pago', p)}><UserPlus />Dar de alta</Button>}
                          <Button size="sm" disabled={saving} onClick={() => facturar('pago', p.id)}><ReceiptText />Factura</Button>
                          <Button size="sm" variant="ghost" onClick={() => ignorar('pago', p.id)}><X />Ignorar</Button>
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
            <CardContent className="p-0">
              <DataTable columns={columnsHistorialPagos} data={historialPagos} emptyMessage="Sin historial todavía." />
            </CardContent>
          </Card>
        </>
      ) : (
        <>
          <Card>
            <CardHeader><CardTitle className="text-base">Transferencias pendientes</CardTitle></CardHeader>
            <CardContent>
              {pendientesMov.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">Sin transferencias pendientes. Usá <strong>Sincronizar</strong> para traer las recibidas.</p>
              ) : (
                <ul className="divide-y">
                  {pendientesMov.map((m) => (
                    <li key={m.id} className="grid gap-2 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="grid gap-1">
                          <p className="font-medium">{formatCurrency(m.monto)} — {m.origen_nombre || m.payer_name || 'Sin datos'} ({m.fecha})</p>
                          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                            <OrigenBadge tipo={m.tipo} metodo={m.origen_banco} />
                            {m.origen_cbu && <code className="text-xs">{m.origen_cbu}</code>}
                            {m.cliente
                              ? <span>Cliente: {m.cliente.name}</span>
                              : m.payer_email
                                ? <span className="flex items-center gap-1"><Mail className="size-3.5" />{m.payer_email}</span>
                                : <span className="flex items-center gap-1"><UserRoundX className="size-3.5" />Sin email</span>}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          {!m.cliente && !m.payer_email && <Button size="sm" variant="outline" onClick={() => abrirCargarEmail(m)}><Mail />Cargar email</Button>}
                          {!m.cliente && (m.payer_email || m.origen_nombre) && <Button size="sm" variant="outline" onClick={() => abrirCrearCliente('mov', m)}><UserPlus />Dar de alta</Button>}
                          <Button size="sm" disabled={saving} onClick={() => facturar('mov', m.id)}><ReceiptText />Factura</Button>
                          <Button size="sm" variant="ghost" onClick={() => ignorar('mov', m.id)}><X />Ignorar</Button>
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
            <CardContent className="p-0">
              <DataTable columns={columnsHistorialMov} data={historialMov} emptyMessage="Sin historial todavía." />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
