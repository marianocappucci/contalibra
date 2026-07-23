import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, MEDIOS_PAGO_LABELS, type Cliente, type Factura, type FacturaDetalle, type TipoFactura,
} from '../api'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { DataTable, sortableHeader } from '@/components/data-table'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

function labelComprobante(f: Factura): string {
  const letra = ({ 1: 'A', 6: 'B', 11: 'C', 3: 'NC-A', 8: 'NC-B', 13: 'NC-C', 2: 'ND-A', 7: 'ND-B', 12: 'ND-C' } as Record<number, string>)[f.tipo] ?? '?'
  const pv = String(f.punto_venta).padStart(4, '0')
  const num = String(f.numero).padStart(8, '0')
  return `${letra} ${pv}-${num}`
}

type ItemRow = { description: string; qty: string; unit_price: string }
const EMPTY_ITEM: ItemRow = { description: '', qty: '1', unit_price: '0' }

const CONDICIONES_VENTA = [
  'Contado', 'Tarjeta de Débito', 'Tarjeta de Crédito', 'Cuenta Corriente',
  'Cheque', 'Transferencia Bancaria', 'Otros medios de pago electrónico', 'Otra',
]

export function Facturas() {
  const { user } = useAuth()
  const [facturas, setFacturas] = useState<Factura[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [vista, setVista] = useState('facturas')
  const [q, setQ] = useState('')

  const [tiposInfo, setTiposInfo] = useState<{ tipos: TipoFactura[]; conceptos: TipoFactura[]; punto_venta: number } | null>(null)
  const [clientes, setClientes] = useState<Cliente[]>([])

  const [creating, setCreating] = useState(false)
  const [tipo, setTipo] = useState('')
  const [clienteId, setClienteId] = useState('')
  const [clienteNombreLibre, setClienteNombreLibre] = useState('')
  const [concepto, setConcepto] = useState('1')
  const [condicionVenta, setCondicionVenta] = useState('Contado')
  const [taxRate, setTaxRate] = useState('0.21')
  const [observations, setObservations] = useState('')
  const [items, setItems] = useState<ItemRow[]>([{ ...EMPTY_ITEM }])
  const [saving, setSaving] = useState(false)

  const [abiertaId, setAbiertaId] = useState<number | null>(null)
  const [detalle, setDetalle] = useState<FacturaDetalle | null>(null)
  const [detalleLoading, setDetalleLoading] = useState(false)
  const [emailTo, setEmailTo] = useState('')
  const [cobroPagos, setCobroPagos] = useState<{ medio: string; monto: string; referencia: string }[]>([{ medio: 'efectivo', monto: '', referencia: '' }])

  useEffect(() => {
    api.get<{ tipos: TipoFactura[]; conceptos: TipoFactura[]; punto_venta: number }>('/api/facturas/tipos').then(setTiposInfo).catch(() => {})
    api.get<Cliente[]>('/api/clientes').then((c) => setClientes(c.filter((x) => x.activo))).catch(() => {})
  }, [])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vista])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ items: Factura[] }>(`/api/facturas?vista=${vista}${q ? `&q=${encodeURIComponent(q)}` : ''}`)
      setFacturas(data.items)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function addItemRow() {
    setItems((rows) => [...rows, { ...EMPTY_ITEM }])
  }
  function removeItemRow(i: number) {
    setItems((rows) => rows.filter((_, idx) => idx !== i))
  }
  function updateItem(i: number, field: keyof ItemRow, value: string) {
    setItems((rows) => rows.map((r, idx) => idx === i ? { ...r, [field]: value } : r))
  }

  const subtotalCalc = items.reduce((acc, r) => acc + (Number(r.qty) || 0) * (Number(r.unit_price) || 0), 0)
  const ivaCalc = tipo === '11' ? 0 : subtotalCalc * (Number(taxRate) || 0)

  function resetForm() {
    setItems([{ ...EMPTY_ITEM }]); setClienteId(''); setClienteNombreLibre('')
    setConcepto('1'); setCondicionVenta('Contado'); setObservations('')
  }

  async function crear() {
    if (!tipo) return
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/facturas', {
        tipo: Number(tipo), punto_venta: tiposInfo?.punto_venta ?? 1, concepto: Number(concepto),
        condicion_venta: condicionVenta, fecha: todayIso(), observations, tax_rate: Number(taxRate) || 0,
        client_id: clienteId ? Number(clienteId) : null, client_name: clienteId ? '' : clienteNombreLibre,
        items: items.filter((r) => r.description.trim()).map((r) => ({
          description: r.description, qty: Number(r.qty) || 0, unit_price: Number(r.unit_price) || 0,
        })),
      })
      setCreating(false)
      resetForm()
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function verDetalle(f: Factura) {
    if (abiertaId === f.id) {
      setAbiertaId(null)
      return
    }
    setAbiertaId(f.id)
    setDetalleLoading(true)
    setError(null)
    try {
      const data = await api.get<FacturaDetalle>(`/api/facturas/${f.id}`)
      setDetalle(data)
      setEmailTo(data.cliente_email || '')
      setCobroPagos([{ medio: 'efectivo', monto: String(data.pendiente || ''), referencia: '' }])
    } catch (err) {
      setError(describeError(err))
    } finally {
      setDetalleLoading(false)
    }
  }

  async function refrescarDetalle() {
    if (abiertaId === null) return
    const data = await api.get<FacturaDetalle>(`/api/facturas/${abiertaId}`)
    setDetalle(data)
  }

  async function autorizar() {
    if (abiertaId === null) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/facturas/${abiertaId}/autorizar`)
      await refrescarDetalle()
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function cobrar() {
    if (abiertaId === null) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/facturas/${abiertaId}/cobrar`, {
        fecha: todayIso(),
        pagos: cobroPagos.filter((p) => Number(p.monto) > 0).map((p) => ({ medio_id: p.medio, monto: Number(p.monto), referencia: p.referencia })),
      })
      await refrescarDetalle()
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function enviarEmail() {
    if (abiertaId === null || !emailTo.trim()) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/facturas/${abiertaId}/enviar-email`, { email: emailTo })
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function crearNota(kind: 'nota-credito' | 'nota-debito') {
    if (abiertaId === null) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/facturas/${abiertaId}/${kind}`)
      setAbiertaId(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  const columns = useMemo<ColumnDef<Factura>[]>(() => [
    { accessorKey: 'numero', header: sortableHeader('Comprobante'), cell: ({ row }) => <span className="font-mono text-sm">{labelComprobante(row.original)}</span> },
    { accessorKey: 'fecha', header: 'Fecha' },
    { accessorKey: 'cliente_razon', header: 'Cliente' },
    { accessorKey: 'total', header: 'Total', cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.total)}</span> },
    {
      accessorKey: 'cae',
      header: 'CAE',
      cell: ({ row }) => row.original.cae && row.original.cae !== 'PENDIENTE'
        ? <Badge variant="default">Autorizada</Badge>
        : <Badge variant="outline">Pendiente</Badge>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => verDetalle(row.original)}>
            {abiertaId === row.original.id ? 'Ocultar' : 'Ver'}
          </Button>
          <Button asChild size="sm" variant="outline"><a href={`/facturas/${row.original.id}/pdf`} target="_blank" rel="noreferrer">PDF</a></Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [abiertaId])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">Facturas</h2>
        <div className="flex items-end gap-3">
          <div className="grid gap-1.5"><Label>Buscar</Label><Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()} className="w-48" /></div>
          <div className="grid gap-1.5">
            <Label>Vista</Label>
            <Select value={vista} onValueChange={setVista}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="facturas">Facturas</SelectItem>
                <SelectItem value="nc">Notas de crédito</SelectItem>
                <SelectItem value="nd">Notas de débito</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {!creating && <Button onClick={() => setCreating(true)}>+ Nueva factura</Button>}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {creating && tiposInfo && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nueva factura</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="grid gap-1.5">
                <Label>Tipo</Label>
                <Select value={tipo} onValueChange={setTipo}>
                  <SelectTrigger className="w-36"><SelectValue placeholder="Elegir…" /></SelectTrigger>
                  <SelectContent>
                    {tiposInfo.tipos.map((t) => <SelectItem key={t.value} value={String(t.value)}>{t.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label>Cliente</Label>
                <Select value={clienteId} onValueChange={(v) => { setClienteId(v); setClienteNombreLibre('') }}>
                  <SelectTrigger className="w-52"><SelectValue placeholder="Elegir cliente…" /></SelectTrigger>
                  <SelectContent>
                    {clientes.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {!clienteId && (
                <div className="grid gap-1.5"><Label>o nombre libre</Label><Input value={clienteNombreLibre} onChange={(e) => setClienteNombreLibre(e.target.value)} className="w-48" placeholder="Consumidor Final" /></div>
              )}
              <div className="grid gap-1.5">
                <Label>Concepto</Label>
                <Select value={concepto} onValueChange={setConcepto}>
                  <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {tiposInfo.conceptos.map((c) => <SelectItem key={c.value} value={String(c.value)}>{c.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label>Condición de venta</Label>
                <Select value={condicionVenta} onValueChange={setCondicionVenta}>
                  <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CONDICIONES_VENTA.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              {tipo !== '11' && (
                <div className="grid gap-1.5"><Label>IVA</Label><Input type="number" step="0.01" value={taxRate} onChange={(e) => setTaxRate(e.target.value)} className="w-24" /></div>
              )}
            </div>

            <div className="grid gap-2">
              <Label>Ítems</Label>
              {items.map((row, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2">
                  <Input value={row.description} onChange={(e) => updateItem(i, 'description', e.target.value)} className="w-64" placeholder="Descripción" />
                  <Input type="number" step="0.01" value={row.qty} onChange={(e) => updateItem(i, 'qty', e.target.value)} className="w-20" placeholder="Cant." />
                  <Input type="number" step="0.01" value={row.unit_price} onChange={(e) => updateItem(i, 'unit_price', e.target.value)} className="w-28" placeholder="Precio unit." />
                  <span className="w-28 text-sm text-muted-foreground">{formatCurrency((Number(row.qty) || 0) * (Number(row.unit_price) || 0))}</span>
                  {items.length > 1 && <Button size="sm" variant="ghost" onClick={() => removeItemRow(i)}>Quitar</Button>}
                </div>
              ))}
              <Button size="sm" variant="outline" className="w-fit" onClick={addItemRow}>+ Agregar ítem</Button>
            </div>

            <div className="grid gap-1.5"><Label>Observaciones</Label><Input value={observations} onChange={(e) => setObservations(e.target.value)} /></div>

            <div className="flex flex-wrap items-end gap-4 border-t pt-4">
              <p className="text-sm">Subtotal: <span className="font-medium">{formatCurrency(subtotalCalc)}</span></p>
              <p className="text-sm">IVA: <span className="font-medium">{formatCurrency(ivaCalc)}</span></p>
              <p className="text-sm">Total: <span className="font-medium">{formatCurrency(subtotalCalc + ivaCalc)}</span></p>
              <Button disabled={saving || !tipo} onClick={crear}>{saving ? 'Emitiendo…' : 'Emitir factura'}</Button>
              <Button type="button" variant="outline" onClick={() => { setCreating(false); resetForm() }}>Cancelar</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={facturas} emptyMessage="Sin comprobantes todavía." />
          )}
        </CardContent>
      </Card>

      {abiertaId !== null && (
        <Card>
          <CardHeader><CardTitle className="text-base">{detalle ? labelComprobante(detalle.factura) : ''} — {detalle?.factura.cliente_razon}</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            {detalleLoading || !detalle ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
            ) : (
              <>
                <div className="grid gap-1 text-sm sm:grid-cols-2">
                  <p>CAE: <span className="font-medium">{detalle.factura.cae && detalle.factura.cae !== 'PENDIENTE' ? detalle.factura.cae : 'Sin autorizar'}</span></p>
                  <p>Vencimiento CAE: <span className="font-medium">{detalle.factura.cae_vto || '—'}</span></p>
                  <p>Cobrado: <span className="font-medium">{formatCurrency(detalle.total_cobrado)}</span></p>
                  <p>Pendiente: <span className="font-medium">{formatCurrency(detalle.pendiente)}</span></p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {(!detalle.factura.cae || detalle.factura.cae === 'PENDIENTE') && (
                    <Button size="sm" variant="outline" disabled={saving} onClick={autorizar}>Reintentar autorización ARCA</Button>
                  )}
                  <Button asChild size="sm" variant="outline"><a href={`/facturas/${abiertaId}/ticket`} target="_blank" rel="noreferrer">Ticket</a></Button>
                  {detalle.cobros.length > 0 && <Button asChild size="sm" variant="outline"><a href={`/facturas/${abiertaId}/recibo`} target="_blank" rel="noreferrer">Recibo</a></Button>}
                  {user?.role === 'admin' && [1, 6, 11].includes(detalle.factura.tipo) && (
                    <>
                      <Button size="sm" variant="outline" disabled={saving} onClick={() => crearNota('nota-credito')}>Nota de crédito</Button>
                      <Button size="sm" variant="outline" disabled={saving} onClick={() => crearNota('nota-debito')}>Nota de débito</Button>
                    </>
                  )}
                </div>

                {detalle.pendiente > 0 && [1, 6, 11].includes(detalle.factura.tipo) && (
                  <div className="grid gap-2 border-t pt-4">
                    <Label>Registrar cobro</Label>
                    {cobroPagos.map((p, i) => (
                      <div key={i} className="flex flex-wrap items-center gap-2">
                        <Select value={p.medio} onValueChange={(v) => setCobroPagos((rows) => rows.map((r, idx) => idx === i ? { ...r, medio: v } : r))}>
                          <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {Object.entries(MEDIOS_PAGO_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <Input type="number" step="0.01" value={p.monto} onChange={(e) => setCobroPagos((rows) => rows.map((r, idx) => idx === i ? { ...r, monto: e.target.value } : r))} className="w-28" />
                        <Input value={p.referencia} onChange={(e) => setCobroPagos((rows) => rows.map((r, idx) => idx === i ? { ...r, referencia: e.target.value } : r))} className="w-40" placeholder="Referencia" />
                      </div>
                    ))}
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" className="w-fit" onClick={() => setCobroPagos((rows) => [...rows, { medio: 'efectivo', monto: '', referencia: '' }])}>+ Agregar medio</Button>
                      <Button size="sm" disabled={saving} onClick={cobrar}>{saving ? 'Guardando…' : 'Registrar cobro'}</Button>
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap items-end gap-3 border-t pt-4">
                  <div className="grid gap-1.5"><Label>Enviar por email</Label><Input type="email" value={emailTo} onChange={(e) => setEmailTo(e.target.value)} className="w-56" /></div>
                  <Button size="sm" variant="outline" disabled={saving || !emailTo.trim()} onClick={enviarEmail}>Enviar</Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
