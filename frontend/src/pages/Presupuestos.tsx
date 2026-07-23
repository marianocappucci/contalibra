import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, ESTADOS_PRESUPUESTO, type Cliente, type Presupuesto } from '../api'
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
  Send, XCircle, CheckCircle2, RefreshCw, Receipt, CheckCheck, Undo2, Mail, Trash2, FileDown, Eye,
} from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

type ItemRow = { description: string; qty: string; unit_price: string }
const EMPTY_ITEM: ItemRow = { description: '', qty: '1', unit_price: '0' }

const estadoVariant: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  aceptado: 'default', enviado: 'secondary', borrador: 'outline', rechazado: 'destructive', vencido: 'destructive', facturado: 'default',
}

export function Presupuestos() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [presupuestos, setPresupuestos] = useState<Presupuesto[]>([])
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [estadoFiltro, setEstadoFiltro] = useState('')

  const [creating, setCreating] = useState(false)
  const [clienteId, setClienteId] = useState('')
  const [clienteNombreLibre, setClienteNombreLibre] = useState('')
  const [validUntil, setValidUntil] = useState('')
  const [taxRate, setTaxRate] = useState('0.21')
  const [observations, setObservations] = useState('')
  const [items, setItems] = useState<ItemRow[]>([{ ...EMPTY_ITEM }])
  const [saving, setSaving] = useState(false)

  const [abiertoId, setAbiertoId] = useState<number | null>(null)
  const [emailTo, setEmailTo] = useState('')

  useEffect(() => {
    api.get<Cliente[]>('/api/clientes').then((c) => setClientes(c.filter((x) => x.activo))).catch(() => {})
  }, [])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estadoFiltro])

  // Deep-link desde el Dashboard: ?nuevo=1 abre el alta, ?ver=<id> abre el detalle
  useEffect(() => {
    const nuevo = searchParams.get('nuevo')
    const ver = searchParams.get('ver')
    if (nuevo === '1') setCreating(true)
    if (ver) setAbiertoId(Number(ver))
    if (nuevo || ver) setSearchParams((p) => { p.delete('nuevo'); p.delete('ver'); return p }, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ items: Presupuesto[] }>(`/api/presupuestos?estado=${estadoFiltro}${q ? `&q=${encodeURIComponent(q)}` : ''}`)
      setPresupuestos(data.items)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function addItem() { setItems((rows) => [...rows, { ...EMPTY_ITEM }]) }
  function removeItem(i: number) { setItems((rows) => rows.filter((_, idx) => idx !== i)) }
  function updateItem(i: number, field: keyof ItemRow, value: string) {
    setItems((rows) => rows.map((r, idx) => idx === i ? { ...r, [field]: value } : r))
  }

  function resetForm() {
    setClienteId(''); setClienteNombreLibre(''); setValidUntil(''); setTaxRate('0.21')
    setObservations(''); setItems([{ ...EMPTY_ITEM }])
  }

  async function crear() {
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/presupuestos', {
        date: todayIso(), valid_until: validUntil, client_id: clienteId ? Number(clienteId) : null,
        client_name: clienteId ? '' : clienteNombreLibre, tax_rate: Number(taxRate) || 0, observations,
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

  async function cambiarEstado(p: Presupuesto, estado: string, convertirRemito = false) {
    setError(null)
    try {
      await api.post(`/api/presupuestos/${p.id}/estado`, { estado, convertir_remito: convertirRemito })
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function enviarEmail(p: Presupuesto) {
    if (!emailTo.trim()) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/presupuestos/${p.id}/enviar-email`, { email: emailTo })
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function eliminar(p: Presupuesto) {
    setError(null)
    try {
      await api.del(`/api/presupuestos/${p.id}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const columns = useMemo<ColumnDef<Presupuesto>[]>(() => [
    { accessorKey: 'number', header: sortableHeader('Número'), cell: ({ row }) => <span className="font-mono text-sm">{row.original.number}</span> },
    { accessorKey: 'date', header: 'Fecha' },
    { accessorKey: 'client_name', header: 'Cliente' },
    { accessorKey: 'total', header: 'Total', cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.total)}</span> },
    {
      accessorKey: 'status',
      header: 'Estado',
      cell: ({ row }) => <Badge variant={estadoVariant[row.original.status] ?? 'outline'}>{row.original.status}</Badge>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => { setAbiertoId(abiertoId === row.original.id ? null : row.original.id); setEmailTo('') }}>
            <Eye />{abiertoId === row.original.id ? 'Ocultar' : 'Ver'}
          </Button>
          <Button asChild size="sm" variant="outline"><a href={`/presupuestos/${row.original.id}/pdf`} target="_blank" rel="noreferrer"><FileDown />PDF</a></Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [abiertoId])

  const presupuestoAbierto = presupuestos.find((p) => p.id === abiertoId)

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">Presupuestos</h2>
        <div className="flex items-end gap-3">
          <div className="grid gap-1.5"><Label>Buscar</Label><Input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()} className="w-48" /></div>
          <div className="grid gap-1.5">
            <Label>Estado</Label>
            <Select value={estadoFiltro || '__todos__'} onValueChange={(v) => setEstadoFiltro(v === '__todos__' ? '' : v)}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__todos__">Todos</SelectItem>
                {ESTADOS_PRESUPUESTO.map((e) => <SelectItem key={e} value={e}>{e}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {!creating && <Button onClick={() => setCreating(true)}>+ Nuevo presupuesto</Button>}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {creating && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nuevo presupuesto</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex flex-wrap items-end gap-3">
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
                <div className="grid gap-1.5"><Label>o nombre libre</Label><Input value={clienteNombreLibre} onChange={(e) => setClienteNombreLibre(e.target.value)} className="w-48" /></div>
              )}
              <div className="grid gap-1.5"><Label>Válido hasta</Label><Input type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} className="w-40" /></div>
              <div className="grid gap-1.5"><Label>IVA</Label><Input type="number" step="0.01" value={taxRate} onChange={(e) => setTaxRate(e.target.value)} className="w-24" /></div>
            </div>

            <div className="grid gap-2">
              <Label>Ítems</Label>
              {items.map((row, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2">
                  <Input value={row.description} onChange={(e) => updateItem(i, 'description', e.target.value)} className="w-64" placeholder="Descripción" />
                  <Input type="number" step="0.01" value={row.qty} onChange={(e) => updateItem(i, 'qty', e.target.value)} className="w-20" placeholder="Cant." />
                  <Input type="number" step="0.01" value={row.unit_price} onChange={(e) => updateItem(i, 'unit_price', e.target.value)} className="w-28" placeholder="Precio" />
                  {items.length > 1 && <Button size="sm" variant="ghost" onClick={() => removeItem(i)}>Quitar</Button>}
                </div>
              ))}
              <Button size="sm" variant="outline" className="w-fit" onClick={addItem}>+ Agregar ítem</Button>
            </div>

            <div className="grid gap-1.5"><Label>Observaciones</Label><Input value={observations} onChange={(e) => setObservations(e.target.value)} /></div>

            <div className="flex gap-2">
              <Button disabled={saving} onClick={crear}>{saving ? 'Guardando…' : 'Crear presupuesto'}</Button>
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
            <DataTable columns={columns} data={presupuestos} emptyMessage="Sin presupuestos todavía." />
          )}
        </CardContent>
      </Card>

      {presupuestoAbierto && (() => {
        const p = presupuestoAbierto
        const st = p.status
        return (
          <div className="grid gap-4">
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
                  <p><span className="text-muted-foreground">Estado:</span> <Badge variant={estadoVariant[st] ?? 'outline'}>{st}</Badge></p>
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
                      <Button size="sm" onClick={() => cambiarEstado(p, 'enviado')}><Send />Marcar como enviado</Button>
                      <Button size="sm" variant="outline" onClick={() => cambiarEstado(p, 'rechazado')}><XCircle />Rechazar</Button>
                    </>
                  )}
                  {(st === 'enviado') && (
                    <>
                      <Button size="sm" onClick={() => cambiarEstado(p, 'aceptado', false)}><CheckCircle2 />Aceptar</Button>
                      <Button size="sm" variant="outline" onClick={() => cambiarEstado(p, 'aceptado', true)}><RefreshCw />Aceptar y convertir a remito</Button>
                      <Button size="sm" variant="outline" onClick={() => cambiarEstado(p, 'rechazado')}><XCircle />Rechazar</Button>
                    </>
                  )}
                  {st === 'aceptado' && (
                    <>
                      <Button asChild size="sm"><a href={`/facturas?nuevo=1`}><Receipt />Generar factura</a></Button>
                      <Button size="sm" variant="outline" onClick={() => cambiarEstado(p, 'facturado')}><CheckCheck />Marcar como facturado</Button>
                      <Button size="sm" variant="outline" onClick={() => cambiarEstado(p, 'rechazado')}><XCircle />Rechazar</Button>
                    </>
                  )}
                  {(st === 'rechazado' || st === 'vencido') && (
                    <Button size="sm" variant="outline" onClick={() => cambiarEstado(p, 'borrador')}><Undo2 />Reactivar como borrador</Button>
                  )}
                  {st === 'borrador' && (
                    <Button size="sm" variant="outline" onClick={() => eliminar(p)}><Trash2 />Eliminar presupuesto</Button>
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
                <Button size="sm" variant="outline" disabled={saving || !emailTo.trim()} onClick={() => enviarEmail(p)}><Mail />Enviar</Button>
              </CardContent>
            </Card>
          </div>
        )
      })()}
    </div>
  )
}
