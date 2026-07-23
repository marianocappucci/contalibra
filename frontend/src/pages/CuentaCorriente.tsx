import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, MEDIOS_PAGO_LABELS, type Caja, type ClienteConSaldoCC, type MovimientoCC,
} from '../api'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
    setMonto(''); setReferencia('')
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
        monto: Number(monto), fecha: todayIso(), referencia,
        medio_pago: medioPago, caja_id: cajaId ? Number(cajaId) : null,
      })
      setMovimientos(data.movimientos)
      setSaldo(data.saldo)
      setMonto(''); setReferencia('')
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setPagando(false)
    }
  }

  async function eliminarPago(pagoId: number) {
    if (abiertoId === null) return
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

  const columns = useMemo<ColumnDef<ClienteConSaldoCC>[]>(() => [
    { accessorKey: 'name', header: sortableHeader('Cliente'), cell: ({ row }) => <span className="font-medium">{row.original.name}</span> },
    { accessorKey: 'cuit_dni', header: 'CUIT/DNI', cell: ({ row }) => row.original.cuit_dni || '—' },
    {
      accessorKey: 'saldo',
      header: 'Saldo',
      cell: ({ row }) => (
        <span className={row.original.saldo > 0 ? 'font-medium text-destructive' : 'font-medium text-emerald-600 dark:text-emerald-400'}>
          {formatCurrency(row.original.saldo)}
        </span>
      ),
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end">
          <Button size="sm" variant="outline" onClick={() => abrir(row.original)}>
            {abiertoId === row.original.id ? 'Ocultar' : 'Ver movimientos'}
          </Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [abiertoId, cajas])

  const movColumns = useMemo<ColumnDef<MovimientoCC>[]>(() => [
    { accessorKey: 'fecha', header: 'Fecha' },
    { accessorKey: 'concepto', header: 'Concepto' },
    {
      accessorKey: 'monto',
      header: 'Monto',
      cell: ({ row }) => (
        <span className={row.original.tipo === 'debito' ? 'text-destructive' : 'text-emerald-600 dark:text-emerald-400'}>
          {row.original.tipo === 'debito' ? '+' : '−'} {formatCurrency(row.original.monto)}
        </span>
      ),
    },
    { accessorKey: 'referencia', header: 'Referencia', cell: ({ row }) => row.original.referencia || '—' },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        row.original.cc_pago_id && user?.role === 'admin' ? (
          <Button size="sm" variant="ghost" onClick={() => eliminarPago(row.original.cc_pago_id!)}>Eliminar</Button>
        ) : null
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [user])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Cuenta corriente</h2>
        <span className="text-sm text-muted-foreground">Deuda total: <span className="font-medium text-foreground">{formatCurrency(totalDeuda)}</span></span>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={clientes} emptyMessage="Sin clientes con movimientos en cuenta corriente." />
          )}
        </CardContent>
      </Card>

      {abiertoId !== null && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{clientes.find((c) => c.id === abiertoId)?.name}</CardTitle>
            <CardDescription>Saldo actual: {formatCurrency(saldo)}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {detalleLoading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
            ) : (
              <>
                <DataTable columns={movColumns} data={movimientos} emptyMessage="Sin movimientos." />
                <div className="flex flex-wrap items-end gap-3 border-t pt-4">
                  <div className="grid gap-1.5"><Label>Monto a pagar</Label><Input type="number" step="0.01" value={monto} onChange={(e) => setMonto(e.target.value)} className="w-32" /></div>
                  <div className="grid gap-1.5">
                    <Label>Caja</Label>
                    <Select value={cajaId} onValueChange={setCajaId}>
                      <SelectTrigger className="w-40"><SelectValue placeholder="Sin caja" /></SelectTrigger>
                      <SelectContent>
                        {cajas.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-1.5">
                    <Label>Medio de pago</Label>
                    <Select value={medioPago} onValueChange={setMedioPago}>
                      <SelectTrigger className="w-44"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(MEDIOS_PAGO_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-1.5"><Label>Referencia</Label><Input value={referencia} onChange={(e) => setReferencia(e.target.value)} className="w-40" /></div>
                  <Button disabled={pagando || !monto} onClick={pagar}>{pagando ? 'Guardando…' : 'Registrar pago'}</Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
