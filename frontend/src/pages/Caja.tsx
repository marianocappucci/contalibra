import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, MEDIOS_PAGO_LABELS, type CajaConfig, type CajaMovimiento, type ResumenCaja } from '../api'
import { Card, CardContent, CardHeader, CardDescription, CardTitle } from '@/components/ui/card'
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

function firstOfMonthIso(): string {
  const d = new Date()
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

export function Caja() {
  const [desde, setDesde] = useState(firstOfMonthIso())
  const [hasta, setHasta] = useState(todayIso())
  const [cajaId, setCajaId] = useState('')
  const [cajas, setCajas] = useState<CajaConfig[]>([])
  const [movimientos, setMovimientos] = useState<CajaMovimiento[]>([])
  const [resumen, setResumen] = useState<ResumenCaja | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [saving, setSaving] = useState(false)

  const [tipo, setTipo] = useState('ingreso')
  const [concepto, setConcepto] = useState('')
  const [monto, setMonto] = useState('')
  const [referencia, setReferencia] = useState('')
  const [formCajaId, setFormCajaId] = useState('')
  const [medioPago, setMedioPago] = useState('efectivo')

  useEffect(() => {
    api.get<CajaConfig[]>('/api/cajas').then(setCajas).catch(() => {})
  }, [])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desde, hasta, cajaId])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ movimientos: CajaMovimiento[]; resumen: ResumenCaja }>(
        `/api/caja?desde=${desde}&hasta=${hasta}${cajaId ? `&caja_id=${cajaId}` : ''}`,
      )
      setMovimientos(data.movimientos)
      setResumen(data.resumen)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function crear() {
    if (!concepto.trim() || !monto) return
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/caja', {
        fecha: todayIso(), tipo, concepto, monto: Number(monto), referencia,
        caja_id: formCajaId ? Number(formCajaId) : null, medio_pago: medioPago,
      })
      setCreating(false)
      setConcepto(''); setMonto(''); setReferencia('')
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function eliminar(mov: CajaMovimiento) {
    setError(null)
    try {
      await api.del(`/api/caja/${mov.id}`)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  const columns = useMemo<ColumnDef<CajaMovimiento>[]>(() => [
    { accessorKey: 'fecha', header: sortableHeader('Fecha') },
    { accessorKey: 'concepto', header: 'Concepto', cell: ({ row }) => <span className="font-medium">{row.original.concepto}</span> },
    { accessorKey: 'caja_nombre', header: 'Caja', cell: ({ row }) => row.original.caja_nombre || '—' },
    { accessorKey: 'medio_pago', header: 'Medio', cell: ({ row }) => MEDIOS_PAGO_LABELS[row.original.medio_pago] ?? row.original.medio_pago ?? '—' },
    { accessorKey: 'usuario_nombre', header: 'Usuario', cell: ({ row }) => row.original.usuario_nombre || '—' },
    {
      accessorKey: 'monto',
      header: 'Monto',
      cell: ({ row }) => (
        <span className={row.original.tipo === 'ingreso' ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}>
          {row.original.tipo === 'ingreso' ? '+' : '−'} {formatCurrency(row.original.monto)}
        </span>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => <Button size="sm" variant="ghost" onClick={() => eliminar(row.original)}>Eliminar</Button>,
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-lg font-semibold">Caja</h2>
        <div className="flex items-end gap-3">
          <div className="grid gap-1.5"><Label>Desde</Label><Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="w-40" /></div>
          <div className="grid gap-1.5"><Label>Hasta</Label><Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="w-40" /></div>
          <div className="grid gap-1.5">
            <Label>Caja</Label>
            <Select value={cajaId} onValueChange={setCajaId}>
              <SelectTrigger className="w-36"><SelectValue placeholder="Todas" /></SelectTrigger>
              <SelectContent>
                {cajas.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {!creating && <Button onClick={() => setCreating(true)}>+ Nuevo movimiento</Button>}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {resumen && (
        <div className="grid gap-4 sm:grid-cols-4">
          <Card><CardHeader><CardDescription>Ingresos</CardDescription><CardTitle className="text-2xl text-emerald-600 dark:text-emerald-400">{formatCurrency(resumen.ingresos)}</CardTitle></CardHeader></Card>
          <Card><CardHeader><CardDescription>Egresos</CardDescription><CardTitle className="text-2xl text-destructive">{formatCurrency(resumen.egresos)}</CardTitle></CardHeader></Card>
          <Card><CardHeader><CardDescription>Saldo del período</CardDescription><CardTitle className="text-2xl">{formatCurrency(resumen.saldo_periodo)}</CardTitle></CardHeader></Card>
          <Card><CardHeader><CardDescription>Saldo total</CardDescription><CardTitle className="text-2xl">{formatCurrency(resumen.saldo_total)}</CardTitle></CardHeader></Card>
        </div>
      )}

      {creating && (
        <Card>
          <CardHeader><CardTitle className="text-base">Nuevo movimiento</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5">
              <Label>Tipo</Label>
              <Select value={tipo} onValueChange={setTipo}>
                <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ingreso">Ingreso</SelectItem>
                  <SelectItem value="egreso">Egreso</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5"><Label>Concepto</Label><Input value={concepto} onChange={(e) => setConcepto(e.target.value)} className="w-52" /></div>
            <div className="grid gap-1.5"><Label>Monto</Label><Input type="number" step="0.01" value={monto} onChange={(e) => setMonto(e.target.value)} className="w-32" /></div>
            <div className="grid gap-1.5">
              <Label>Caja</Label>
              <Select value={formCajaId} onValueChange={setFormCajaId}>
                <SelectTrigger className="w-36"><SelectValue placeholder="Por defecto" /></SelectTrigger>
                <SelectContent>
                  {cajas.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label>Medio</Label>
              <Select value={medioPago} onValueChange={setMedioPago}>
                <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(MEDIOS_PAGO_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5"><Label>Referencia</Label><Input value={referencia} onChange={(e) => setReferencia(e.target.value)} className="w-40" /></div>
            <Button disabled={saving} onClick={crear}>{saving ? 'Guardando…' : 'Crear'}</Button>
            <Button type="button" variant="outline" onClick={() => setCreating(false)}>Cancelar</Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={movimientos} emptyMessage="Sin movimientos en el período." />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
