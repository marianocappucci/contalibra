import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, MEDIOS_PAGO_LABELS, type Caja, type ClienteConSaldoCC, type MovimientoCC,
} from '../api'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  BookOpen, Eye, EyeOff, CircleDollarSign, Trash2, ArrowUpCircle, ArrowDownCircle,
  ShoppingCart, Receipt,
} from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

export function CuentaCorriente() {
  const { user } = useAuth()
  const [clientes, setClientes] = useState<ClienteConSaldoCC[]>([])
  const [totalDeuda, setTotalDeuda] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [abiertoId, setAbiertoId] = useState<number | null>(null)
  const [movimientos, setMovimientos] = useState<MovimientoCC[]>([])
  const [saldo, setSaldo] = useState(0)
  const [cajas, setCajas] = useState<Caja[]>([])
  const [detalleLoading, setDetalleLoading] = useState(false)

  const [monto, setMonto] = useState('')
  const [fecha, setFecha] = useState(todayIso())
  const [concepto, setConcepto] = useState('Pago a cuenta')
  const [medioPago, setMedioPago] = useState('efectivo')
  const [cajaId, setCajaId] = useState('')
  const [referencia, setReferencia] = useState('')
  const [pagando, setPagando] = useState(false)

  useEffect(() => {
    load()
    api.get<Caja[]>('/api/cuenta-corriente/cajas').then(setCajas).catch(() => {})
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ clientes: ClienteConSaldoCC[]; total_deuda: number }>('/api/cuenta-corriente')
      setClientes(data.clientes)
      setTotalDeuda(data.total_deuda)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function abrir(cliente: ClienteConSaldoCC) {
    if (abiertoId === cliente.id) {
      setAbiertoId(null)
      return
    }
    setAbiertoId(cliente.id)
    setDetalleLoading(true)
    setError(null)
    setMonto(''); setReferencia(''); setFecha(todayIso()); setConcepto('Pago a cuenta')
    try {
      const data = await api.get<{ movimientos: MovimientoCC[]; saldo: number }>(`/api/cuenta-corriente/${cliente.id}`)
      setMovimientos(data.movimientos)
      setSaldo(data.saldo)
      const caja = cajas.find((c) => c.es_default) ?? cajas[0]
      setCajaId(caja ? String(caja.id) : '')
      setMedioPago(caja?.medios_pago[0] ?? 'efectivo')
    } catch (err) {
      setError(describeError(err))
    } finally {
      setDetalleLoading(false)
    }
  }

  async function pagar() {
    if (abiertoId === null || !monto) return
    setPagando(true)
    setError(null)
    try {
      const data = await api.post<{ movimientos: MovimientoCC[]; saldo: number }>(`/api/cuenta-corriente/${abiertoId}/pagar`, {
        monto: Number(monto), fecha, concepto: concepto || 'Pago a cuenta', referencia,
        medio_pago: medioPago, caja_id: cajaId ? Number(cajaId) : null,
      })
      setMovimientos(data.movimientos)
      setSaldo(data.saldo)
      setMonto(''); setReferencia(''); setConcepto('Pago a cuenta')
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setPagando(false)
    }
  }

  async function eliminarPago(pagoId: number) {
    if (abiertoId === null) return
    if (!window.confirm('¿Eliminar este pago?')) return
    setError(null)
    try {
      await api.del(`/api/cuenta-corriente/pagos/${pagoId}`)
      const data = await api.get<{ movimientos: MovimientoCC[]; saldo: number }>(`/api/cuenta-corriente/${abiertoId}`)
      setMovimientos(data.movimientos)
      setSaldo(data.saldo)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const totales = useMemo(() => {
    let cargado = 0
    let abonado = 0
    for (const m of movimientos) {
      if (m.tipo === 'debito') cargado += m.monto
      else abonado += m.monto
    }
    return { cargado, abonado }
  }, [movimientos])

  const columns = useMemo<ColumnDef<ClienteConSaldoCC>[]>(() => [
    { accessorKey: 'name', header: sortableHeader('Cliente'), cell: ({ row }) => <span className="font-semibold">{row.original.name}</span> },
    { accessorKey: 'cuit_dni', header: 'CUIT/DNI', cell: ({ row }) => <span className="font-mono text-sm text-muted-foreground">{row.original.cuit_dni || '—'}</span> },
    {
      accessorKey: 'saldo',
      header: () => <div className="text-right">Saldo</div>,
      cell: ({ row }) => {
        const s = row.original.saldo
        return (
          <div className="text-right">
            {s > 0 ? (
              <Badge className="bg-amber-500/15 text-amber-700 hover:bg-amber-500/15 dark:text-amber-400">{formatCurrency(s)}</Badge>
            ) : s < 0 ? (
              <Badge className="bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-400">A favor {formatCurrency(s * -1)}</Badge>
            ) : (
              <Badge variant="secondary">{formatCurrency(0)}</Badge>
            )}
          </div>
        )
      },
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end">
          <Button size="sm" variant="outline" onClick={() => abrir(row.original)}>
            {abiertoId === row.original.id ? <><EyeOff />Ocultar</> : <><Eye />Ver</>}
          </Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [abiertoId, cajas])

  const movColumns = useMemo<ColumnDef<MovimientoCC>[]>(() => [
    { accessorKey: 'fecha', header: 'Fecha' },
    {
      accessorKey: 'tipo',
      header: 'Tipo',
      cell: ({ row }) => (
        row.original.tipo === 'debito'
          ? <Badge variant="destructive"><ArrowUpCircle />Cargo</Badge>
          : <Badge className="bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-400"><ArrowDownCircle />Abono</Badge>
      ),
    },
    {
      accessorKey: 'concepto',
      header: 'Concepto',
      cell: ({ row }) => {
        if (row.original.venta_id) {
          return <Link to={`/ventas?ver=${row.original.venta_id}`} className="flex items-center gap-1 font-medium text-primary hover:underline"><ShoppingCart className="size-3.5" />{row.original.concepto}</Link>
        }
        if (row.original.factura_id) {
          return <Link to={`/facturas?ver=${row.original.factura_id}`} className="flex items-center gap-1 font-medium text-primary hover:underline"><Receipt className="size-3.5" />{row.original.concepto}</Link>
        }
        return row.original.concepto
      },
    },
    { accessorKey: 'usuario_nombre', header: 'Usuario', cell: ({ row }) => <span className="text-sm">{row.original.usuario_nombre || '—'}</span> },
    {
      accessorKey: 'referencia',
      header: 'Referencia / Medio',
      cell: ({ row }) => (
        <span className="flex flex-wrap items-center gap-1 text-muted-foreground">
          {row.original.referencia || '—'}
          {row.original.medio && <Badge variant="outline">{MEDIOS_PAGO_LABELS[row.original.medio] ?? row.original.medio}</Badge>}
        </span>
      ),
    },
    {
      accessorKey: 'monto',
      header: () => <div className="text-right">Monto</div>,
      cell: ({ row }) => (
        <div className={`text-right font-semibold ${row.original.tipo === 'debito' ? 'text-destructive' : 'text-emerald-600 dark:text-emerald-400'}`}>
          {row.original.tipo === 'debito' ? '+' : '−'} {formatCurrency(row.original.monto)}
        </div>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        row.original.cc_pago_id && user?.role === 'admin' ? (
          <Button size="sm" variant="ghost" onClick={() => eliminarPago(row.original.cc_pago_id!)}><Trash2 />Eliminar</Button>
        ) : null
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [user])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><BookOpen className="size-5 text-primary" />Cuenta Corriente</h2>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {totalDeuda > 0 && (
        <Card className="border-0 bg-amber-50 dark:bg-amber-950/40">
          <CardContent className="py-3 text-center">
            <p className="text-sm text-muted-foreground">Total deuda pendiente</p>
            <p className="text-xl font-bold text-amber-600 dark:text-amber-400">{formatCurrency(totalDeuda)}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base font-semibold">Clientes con cuenta corriente</CardTitle>
          <span className="text-sm font-normal text-muted-foreground">{clientes.length} cliente{clientes.length !== 1 ? 's' : ''}</span>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={clientes} emptyMessage="No hay clientes con movimientos en cuenta corriente." />
          )}
        </CardContent>
      </Card>

      {abiertoId !== null && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              {clientes.find((c) => c.id === abiertoId)?.name}
              {saldo > 0 ? (
                <Badge className="bg-amber-500/15 text-amber-700 hover:bg-amber-500/15 dark:text-amber-400">Debe {formatCurrency(saldo)}</Badge>
              ) : saldo < 0 ? (
                <Badge className="bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-400">A favor {formatCurrency(saldo * -1)}</Badge>
              ) : (
                <Badge variant="secondary">Saldo $0</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            {detalleLoading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
            ) : (
              <>
                <div className="grid gap-4 sm:grid-cols-3">
                  <Card><CardHeader><CardDescription>Total cargado</CardDescription><CardTitle className="text-xl text-destructive">{formatCurrency(totales.cargado)}</CardTitle></CardHeader></Card>
                  <Card><CardHeader><CardDescription>Total abonado</CardDescription><CardTitle className="text-xl text-emerald-600 dark:text-emerald-400">{formatCurrency(totales.abonado)}</CardTitle></CardHeader></Card>
                  <Card><CardHeader><CardDescription>Saldo actual</CardDescription><CardTitle className={saldo > 0 ? 'text-xl text-amber-600 dark:text-amber-400' : 'text-xl text-emerald-600 dark:text-emerald-400'}>{formatCurrency(saldo)}</CardTitle></CardHeader></Card>
                </div>

                <DataTable columns={movColumns} data={movimientos} emptyMessage="Sin movimientos." />

                <div className="grid gap-3 border-t pt-4">
                  <p className="flex items-center gap-2 text-sm font-medium"><CircleDollarSign className="size-4" />Registrar pago</p>
                  {saldo > 0 && (
                    <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm dark:border-amber-900 dark:bg-amber-950/40">
                      Saldo pendiente: <strong>{formatCurrency(saldo)}</strong>
                    </p>
                  )}
                  <div className="flex flex-wrap items-end gap-3">
                    <div className="grid gap-1.5"><Label>Monto</Label><Input type="number" step="0.01" value={monto} onChange={(e) => setMonto(e.target.value)} className="w-32" /></div>
                    <div className="grid gap-1.5"><Label>Fecha</Label><Input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="w-40" /></div>
                    <div className="grid gap-1.5"><Label>Concepto</Label><Input value={concepto} onChange={(e) => setConcepto(e.target.value)} className="w-48" /></div>
                    <div className="grid gap-1.5">
                      <Label>Medio de pago</Label>
                      <Select value={medioPago} onValueChange={setMedioPago}>
                        <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {Object.entries(MEDIOS_PAGO_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid gap-1.5"><Label>Referencia <span className="font-normal text-muted-foreground">(opcional)</span></Label><Input value={referencia} onChange={(e) => setReferencia(e.target.value)} className="w-40" placeholder="N° transferencia, cheque…" /></div>
                    {cajas.length > 0 && (
                      <div className="grid gap-1.5">
                        <Label>Registrar en caja <span className="font-normal text-muted-foreground">(opcional)</span></Label>
                        <Select value={cajaId || 'ninguna'} onValueChange={(v) => setCajaId(v === 'ninguna' ? '' : v)}>
                          <SelectTrigger className="w-48"><SelectValue placeholder="— No registrar en caja —" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="ninguna">— No registrar en caja —</SelectItem>
                            {cajas.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                    <Button disabled={pagando || !monto} onClick={pagar}><CircleDollarSign />{pagando ? 'Guardando…' : 'Registrar pago'}</Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
