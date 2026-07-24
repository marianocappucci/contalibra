import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api, ApiError, type Cliente, type Factura, type TipoFactura } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { Plus, Receipt } from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

type ItemRow = { description: string; qty: string; unit_price: string }
const EMPTY_ITEM: ItemRow = { description: '', qty: '1', unit_price: '0' }

const CONDICIONES_VENTA = [
  'Contado', 'Tarjeta de Débito', 'Tarjeta de Crédito', 'Cuenta Corriente',
  'Cheque', 'Transferencia Bancaria', 'Otros medios de pago electrónico', 'Otra',
]

// Prefill opcional para "Duplicar" (FacturaDetalle.tsx) o "Generar factura"
// desde un presupuesto aceptado (PresupuestoDetalle.tsx) — navigate con
// state, en vez de query string, para no tener que serializar los items.
type PrefillState = {
  tipo?: string; clienteId?: string; clienteNombreLibre?: string; concepto?: string
  condicionVenta?: string; taxRate?: string; items?: ItemRow[]; observations?: string
  fchServDesde?: string; fchServHasta?: string; fchVtoPago?: string
}

export function FacturaNueva() {
  const navigate = useNavigate()
  const location = useLocation()
  const prefill = (location.state as PrefillState | null) ?? null

  const [tiposInfo, setTiposInfo] = useState<{ tipos: TipoFactura[]; conceptos: TipoFactura[]; punto_venta: number } | null>(null)
  const [clientes, setClientes] = useState<Cliente[]>([])

  const [tipo, setTipo] = useState(prefill?.tipo ?? '')
  const [clienteId, setClienteId] = useState(prefill?.clienteId ?? '')
  const [clienteNombreLibre, setClienteNombreLibre] = useState(prefill?.clienteNombreLibre ?? '')
  const [concepto, setConcepto] = useState(prefill?.concepto ?? '1')
  const [condicionVenta, setCondicionVenta] = useState(prefill?.condicionVenta ?? 'Contado')
  const [taxRate, setTaxRate] = useState(prefill?.taxRate ?? '0.21')
  const [observations, setObservations] = useState(prefill?.observations ?? '')
  const [items, setItems] = useState<ItemRow[]>(prefill?.items ?? [{ ...EMPTY_ITEM }])
  const [fchServDesde, setFchServDesde] = useState(prefill?.fchServDesde ?? todayIso())
  const [fchServHasta, setFchServHasta] = useState(prefill?.fchServHasta ?? todayIso())
  const [fchVtoPago, setFchVtoPago] = useState(prefill?.fchVtoPago ?? todayIso())
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const requiereFechasServicio = concepto === '2' || concepto === '3'

  useEffect(() => {
    api.get<{ tipos: TipoFactura[]; conceptos: TipoFactura[]; punto_venta: number }>('/api/facturas/tipos').then(setTiposInfo).catch(() => {})
    api.get<Cliente[]>('/api/clientes').then((c) => setClientes(c.filter((x) => x.activo))).catch(() => {})
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
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

  async function crear() {
    if (!tipo) return
    setSaving(true)
    setError(null)
    try {
      const factura = await api.post<Factura>('/api/facturas', {
        tipo: Number(tipo), punto_venta: tiposInfo?.punto_venta ?? 1, concepto: Number(concepto),
        condicion_venta: condicionVenta, fecha: todayIso(), observations, tax_rate: Number(taxRate) || 0,
        client_id: clienteId ? Number(clienteId) : null, client_name: clienteId ? '' : clienteNombreLibre,
        items: items.filter((r) => r.description.trim()).map((r) => ({
          description: r.description, qty: Number(r.qty) || 0, unit_price: Number(r.unit_price) || 0,
        })),
        ...(requiereFechasServicio
          ? { fch_serv_desde: fchServDesde, fch_serv_hasta: fchServHasta, fch_vto_pago: fchVtoPago }
          : {}),
      })
      navigate(`/facturas/${factura.id}`)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold"><Receipt className="size-5 text-primary" />Nueva factura</h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {tiposInfo && (
        <Card>
          <CardHeader><CardTitle className="text-base">Datos del comprobante</CardTitle></CardHeader>
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

            {requiereFechasServicio && (
              <div className="grid gap-3 rounded-md border border-amber-300 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/40">
                <p className="text-sm font-medium">
                  Período de servicio <span className="font-normal text-muted-foreground">— requerido por ARCA cuando el concepto es Servicios</span>
                </p>
                <div className="flex flex-wrap gap-3">
                  <div className="grid gap-1.5"><Label>Fecha desde</Label><Input type="date" value={fchServDesde} onChange={(e) => setFchServDesde(e.target.value)} className="w-40" /></div>
                  <div className="grid gap-1.5"><Label>Fecha hasta</Label><Input type="date" value={fchServHasta} onChange={(e) => setFchServHasta(e.target.value)} className="w-40" /></div>
                  <div className="grid gap-1.5"><Label>Vto. de pago</Label><Input type="date" value={fchVtoPago} onChange={(e) => setFchVtoPago(e.target.value)} className="w-40" /></div>
                </div>
              </div>
            )}

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
              <Button size="sm" variant="outline" className="w-fit" onClick={addItemRow}><Plus />Agregar ítem</Button>
            </div>

            <div className="grid gap-1.5"><Label>Observaciones</Label><Input value={observations} onChange={(e) => setObservations(e.target.value)} /></div>

            <div className="flex flex-wrap items-end gap-4 border-t pt-4">
              <p className="text-sm">Subtotal: <span className="font-medium">{formatCurrency(subtotalCalc)}</span></p>
              <p className="text-sm">IVA: <span className="font-medium">{formatCurrency(ivaCalc)}</span></p>
              <p className="text-sm">Total: <span className="font-medium">{formatCurrency(subtotalCalc + ivaCalc)}</span></p>
              <Button disabled={saving || !tipo} onClick={crear}>{saving ? 'Emitiendo…' : 'Emitir factura'}</Button>
              <Button type="button" variant="outline" onClick={() => navigate('/facturas')}>Cancelar</Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
