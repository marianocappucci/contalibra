import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  api, ApiError, IVA_CONDITIONS, MEDIOS_PAGO_LABELS, type Cliente, type ListaPrecio, type ProductoBusqueda, type Venta,
} from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { ShoppingCart, Plus, UserPlus, X, CheckCircle2 } from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

type ItemRow = { nombre: string; qty: string; precio: string; producto_id: number | null }
type PagoRow = { medio: string; monto: string; referencia: string }

const EMPTY_ITEM: ItemRow = { nombre: '', qty: '1', precio: '0', producto_id: null }
const EMPTY_PAGO: PagoRow = { medio: 'efectivo', monto: '', referencia: '' }

export function VentaNueva() {
  const navigate = useNavigate()
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [listasPrecio, setListasPrecio] = useState<ListaPrecio[]>([])
  const [error, setError] = useState<string | null>(null)

  const [items, setItems] = useState<ItemRow[]>([{ ...EMPTY_ITEM }])
  const [pagos, setPagos] = useState<PagoRow[]>([{ ...EMPTY_PAGO }])
  const [clienteId, setClienteId] = useState('')
  const [listaPrecioId, setListaPrecioId] = useState('')
  const [descuento, setDescuento] = useState('0')
  const [observaciones, setObservaciones] = useState('')
  const [saving, setSaving] = useState(false)
  const [sugerencias, setSugerencias] = useState<{ index: number; items: ProductoBusqueda[] } | null>(null)

  const [nuevoCliente, setNuevoCliente] = useState(false)
  const [ncNombre, setNcNombre] = useState('')
  const [ncCuit, setNcCuit] = useState('')
  const [ncIva, setNcIva] = useState('')
  const [ncEmail, setNcEmail] = useState('')
  const [ncPhone, setNcPhone] = useState('')
  const [ncSaving, setNcSaving] = useState(false)

  useEffect(() => {
    api.get<Cliente[]>('/api/clientes').then((c) => setClientes(c.filter((x) => x.activo))).catch(() => {})
    api.get<ListaPrecio[]>('/api/listas-precio').then(setListasPrecio).catch(() => {})
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function buscarProducto(index: number, texto: string) {
    updateItem(index, 'nombre', texto)
    if (texto.trim().length < 2) {
      setSugerencias(null)
      return
    }
    try {
      const lp = listaPrecioId ? `&lista_id=${listaPrecioId}` : ''
      const res = await api.get<ProductoBusqueda[]>(`/productos/buscar?q=${encodeURIComponent(texto)}${lp}`)
      setSugerencias({ index, items: res })
    } catch {
      setSugerencias(null)
    }
  }

  function elegirProducto(index: number, p: ProductoBusqueda) {
    setItems((rows) => rows.map((r, i) => i === index ? { nombre: p.nombre, qty: r.qty || '1', precio: String(p.precio_venta), producto_id: p.id } : r))
    setSugerencias(null)
  }

  function updateItem(index: number, field: keyof ItemRow, value: string) {
    setItems((rows) => rows.map((r, i) => i === index ? { ...r, [field]: value, ...(field === 'nombre' ? { producto_id: null } : {}) } : r))
  }

  function addItemRow() {
    setItems((rows) => [...rows, { ...EMPTY_ITEM }])
  }

  function removeItemRow(index: number) {
    setItems((rows) => rows.filter((_, i) => i !== index))
  }

  function updatePago(index: number, field: keyof PagoRow, value: string) {
    setPagos((rows) => rows.map((r, i) => i === index ? { ...r, [field]: value } : r))
  }

  function addPagoRow() {
    setPagos((rows) => [...rows, { ...EMPTY_PAGO }])
  }

  function removePagoRow(index: number) {
    setPagos((rows) => rows.filter((_, i) => i !== index))
  }

  const subtotalCalc = items.reduce((acc, r) => acc + (Number(r.qty) || 0) * (Number(r.precio) || 0), 0)
  const totalCalc = Math.max(0, subtotalCalc - (Number(descuento) || 0))
  const pagadoCalc = pagos.reduce((acc, p) => acc + (Number(p.monto) || 0), 0)
  const difCalc = Math.round((totalCalc - pagadoCalc) * 100) / 100

  async function crear() {
    setSaving(true)
    setError(null)
    try {
      const venta = await api.post<Venta>('/api/ventas', {
        fecha: todayIso(),
        items: items.filter((r) => r.nombre.trim() && Number(r.qty) > 0).map((r) => ({
          nombre: r.nombre, qty: Number(r.qty), precio: Number(r.precio) || 0, producto_id: r.producto_id,
        })),
        descuento: Number(descuento) || 0,
        cliente_id: clienteId ? Number(clienteId) : null,
        observaciones,
        pagos: pagos.filter((p) => Number(p.monto) > 0).map((p) => ({ medio: p.medio, monto: Number(p.monto), referencia: p.referencia })),
      })
      navigate(`/ventas/${venta.id}`)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function crearClienteRapido() {
    if (!ncNombre.trim()) return
    setNcSaving(true)
    setError(null)
    try {
      const nuevo = await api.post<Cliente>('/api/clientes', {
        name: ncNombre.trim(), cuit_dni: ncCuit.trim(), iva_condition: ncIva, email: ncEmail.trim(), phone: ncPhone.trim(),
      })
      setClientes((prev) => [...prev, nuevo])
      setClienteId(String(nuevo.id))
      setNuevoCliente(false)
      setNcNombre(''); setNcCuit(''); setNcIva(''); setNcEmail(''); setNcPhone('')
    } catch (err) {
      setError(describeError(err))
    } finally {
      setNcSaving(false)
    }
  }

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold"><ShoppingCart className="size-5 text-primary" />Nueva venta</h2>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader><CardTitle className="text-base">Datos de la venta</CardTitle></CardHeader>
        <CardContent className="grid gap-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5">
              <Label>Cliente</Label>
              <div className="flex items-center gap-1">
                <Select value={clienteId} onValueChange={setClienteId}>
                  <SelectTrigger className="w-52"><SelectValue placeholder="Consumidor Final" /></SelectTrigger>
                  <SelectContent>
                    {clientes.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Button type="button" size="icon" variant="outline" title="Agregar nuevo cliente" onClick={() => setNuevoCliente((v) => !v)}>
                  <UserPlus />
                </Button>
              </div>
            </div>
            {listasPrecio.length > 0 && (
              <div className="grid gap-1.5">
                <Label>Lista de precios</Label>
                <Select value={listaPrecioId || '__base__'} onValueChange={(v) => setListaPrecioId(v === '__base__' ? '' : v)}>
                  <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__base__">— Precio de venta —</SelectItem>
                    {listasPrecio.map((l) => <SelectItem key={l.id} value={String(l.id)}>{l.nombre}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="grid gap-1.5"><Label>Observaciones</Label><Input value={observaciones} onChange={(e) => setObservaciones(e.target.value)} className="w-64" /></div>
          </div>

          {nuevoCliente && (
            <div className="flex flex-wrap items-end gap-3 rounded-md border bg-muted/30 p-3">
              <div className="grid gap-1.5"><Label>Nombre *</Label><Input value={ncNombre} onChange={(e) => setNcNombre(e.target.value)} className="w-44" /></div>
              <div className="grid gap-1.5"><Label>CUIT/DNI</Label><Input value={ncCuit} onChange={(e) => setNcCuit(e.target.value)} className="w-32" /></div>
              <div className="grid gap-1.5">
                <Label>Condición IVA</Label>
                <Select value={ncIva || '__none__'} onValueChange={(v) => setNcIva(v === '__none__' ? '' : v)}>
                  <SelectTrigger className="w-44"><SelectValue placeholder="— Sin especificar —" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">— Sin especificar —</SelectItem>
                    {IVA_CONDITIONS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5"><Label>Email</Label><Input type="email" value={ncEmail} onChange={(e) => setNcEmail(e.target.value)} className="w-44" /></div>
              <div className="grid gap-1.5"><Label>Teléfono</Label><Input value={ncPhone} onChange={(e) => setNcPhone(e.target.value)} className="w-36" /></div>
              <Button size="sm" disabled={ncSaving || !ncNombre.trim()} onClick={crearClienteRapido}><UserPlus />{ncSaving ? 'Guardando…' : 'Crear cliente'}</Button>
              <Button size="sm" type="button" variant="ghost" onClick={() => setNuevoCliente(false)}>Cancelar</Button>
            </div>
          )}

          <div className="grid gap-2">
            <Label>Ítems</Label>
            {items.map((row, i) => (
              <div key={i} className="relative flex flex-wrap items-center gap-2">
                <Input
                  value={row.nombre} onChange={(e) => buscarProducto(i, e.target.value)}
                  placeholder="Producto o descripción…" className="w-56"
                />
                {sugerencias?.index === i && sugerencias.items.length > 0 && (
                  <div className="absolute top-9 left-0 z-10 w-56 rounded-md border bg-popover shadow-md">
                    {sugerencias.items.map((p) => (
                      <button
                        key={p.id} type="button"
                        className="block w-full px-3 py-1.5 text-left text-sm hover:bg-accent"
                        onClick={() => elegirProducto(i, p)}
                      >
                        {p.nombre} — {formatCurrency(p.precio_venta)}
                      </button>
                    ))}
                  </div>
                )}
                <Input type="number" step="0.01" value={row.qty} onChange={(e) => updateItem(i, 'qty', e.target.value)} className="w-20" placeholder="Cant." />
                <Input type="number" step="0.01" value={row.precio} onChange={(e) => updateItem(i, 'precio', e.target.value)} className="w-28" placeholder="Precio" />
                <span className="w-28 text-sm text-muted-foreground">{formatCurrency((Number(row.qty) || 0) * (Number(row.precio) || 0))}</span>
                {items.length > 1 && <Button size="sm" variant="ghost" onClick={() => removeItemRow(i)}><X />Quitar</Button>}
              </div>
            ))}
            <Button size="sm" variant="outline" className="w-fit" onClick={addItemRow}><Plus />Agregar ítem</Button>
          </div>

          <div className="grid gap-2">
            <Label>Pagos</Label>
            {pagos.map((row, i) => (
              <div key={i} className="flex flex-wrap items-center gap-2">
                <Select value={row.medio} onValueChange={(v) => updatePago(i, 'medio', v)}>
                  <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(MEDIOS_PAGO_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Input type="number" step="0.01" value={row.monto} onChange={(e) => updatePago(i, 'monto', e.target.value)} className="w-28" placeholder="Monto" />
                <Input value={row.referencia} onChange={(e) => updatePago(i, 'referencia', e.target.value)} className="w-40" placeholder="Referencia" />
                {pagos.length > 1 && <Button size="sm" variant="ghost" onClick={() => removePagoRow(i)}><X />Quitar</Button>}
              </div>
            ))}
            <Button size="sm" variant="outline" className="w-fit" onClick={addPagoRow}><Plus />Agregar pago</Button>
            {Math.abs(difCalc) > 0.01 && (
              <p className="text-sm text-amber-700 dark:text-amber-400">
                {difCalc > 0 ? `Falta cubrir ${formatCurrency(difCalc)}` : `Vuelto: ${formatCurrency(Math.abs(difCalc))}`}
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-end gap-4 border-t pt-4">
            <div className="grid gap-1.5"><Label>Descuento</Label><Input type="number" step="0.01" value={descuento} onChange={(e) => setDescuento(e.target.value)} className="w-28" /></div>
            <p className="text-sm">Subtotal: <span className="font-medium">{formatCurrency(subtotalCalc)}</span></p>
            <p className="text-sm">Total: <span className="font-medium">{formatCurrency(totalCalc)}</span></p>
            <Button disabled={saving} onClick={crear}><CheckCircle2 />{saving ? 'Guardando…' : 'Registrar venta'}</Button>
            <Button type="button" variant="outline" onClick={() => navigate('/ventas')}>Cancelar</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
