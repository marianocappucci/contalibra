import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, TIPOS_CUENTA_TESORERIA, type CuentaTesoreria, type MovimientoTesoreria,
} from '../api'
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
  Landmark, Plus, Pencil, Trash2, List, ArrowLeftRight, Check,
  ArrowDownCircle, ArrowUpCircle, ArrowDownLeft, ArrowUpRight, EyeOff,
} from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

const EMPTY_CUENTA = { nombre: '', tipo: 'banco', banco: '', numero: '', descripcion: '', saldo_inicial: '0' }

function MovTipoBadge({ m }: { m: MovimientoTesoreria }) {
  if (m.tipo === 'ingreso') {
    return <Badge className="bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-400"><ArrowDownCircle />Ingreso</Badge>
  }
  if (m.tipo === 'egreso') {
    return <Badge variant="destructive"><ArrowUpCircle />Egreso</Badge>
  }
  if (m.tipo === 'transferencia_entrada') {
    return <Badge variant="outline"><ArrowDownLeft />desde {m.cuenta_destino_nombre}</Badge>
  }
  if (m.tipo === 'transferencia_salida') {
    return <Badge variant="outline"><ArrowUpRight />hacia {m.cuenta_destino_nombre}</Badge>
  }
  return <Badge variant="outline">{m.tipo}</Badge>
}

export function Tesoreria() {
  const [cuentas, setCuentas] = useState<CuentaTesoreria[]>([])
  const [movimientos, setMovimientos] = useState<MovimientoTesoreria[]>([])
  const [totalGeneral, setTotalGeneral] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [editingId, setEditingId] = useState<number | 'new' | null>(null)
  const [form, setForm] = useState(EMPTY_CUENTA)
  const [saving, setSaving] = useState(false)

  const [abiertaId, setAbiertaId] = useState<number | null>(null)
  const [movsCuenta, setMovsCuenta] = useState<MovimientoTesoreria[]>([])
  const [movTipo, setMovTipo] = useState('ingreso')
  const [movMonto, setMovMonto] = useState('')
  const [movConcepto, setMovConcepto] = useState('')
  const [movReferencia, setMovReferencia] = useState('')

  const [tOrigen, setTOrigen] = useState('')
  const [tDestino, setTDestino] = useState('')
  const [tMonto, setTMonto] = useState('')
  const [tConcepto, setTConcepto] = useState('Transferencia entre cuentas')
  const [transfiriendo, setTransfiriendo] = useState(false)

  useEffect(() => { load() }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ cuentas: CuentaTesoreria[]; movimientos: MovimientoTesoreria[]; resumen: { total: number } }>('/api/tesoreria')
      setCuentas(data.cuentas)
      setMovimientos(data.movimientos)
      setTotalGeneral(data.resumen.total)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function startCreate() {
    setEditingId('new')
    setForm(EMPTY_CUENTA)
  }

  function startEdit(c: CuentaTesoreria) {
    setEditingId(c.id)
    setForm({ nombre: c.nombre, tipo: c.tipo, banco: c.banco ?? '', numero: c.numero ?? '', descripcion: c.descripcion ?? '', saldo_inicial: String(c.saldo_inicial) })
  }

  async function guardarCuenta() {
    if (!form.nombre.trim()) return
    setSaving(true)
    setError(null)
    try {
      const payload = { ...form, saldo_inicial: Number(form.saldo_inicial) || 0 }
      if (editingId === 'new') {
        await api.post('/api/tesoreria/cuentas', payload)
      } else if (editingId) {
        await api.put(`/api/tesoreria/cuentas/${editingId}`, payload)
      }
      setEditingId(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function eliminarCuenta(c: CuentaTesoreria) {
    if (!window.confirm(`¿Archivar la cuenta «${c.nombre}»? Los movimientos se conservan.`)) return
    setError(null)
    try {
      await api.del(`/api/tesoreria/cuentas/${c.id}`)
      if (abiertaId === c.id) setAbiertaId(null)
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function abrir(c: CuentaTesoreria) {
    if (abiertaId === c.id) {
      setAbiertaId(null)
      return
    }
    setAbiertaId(c.id)
    setMovTipo('ingreso'); setMovMonto(''); setMovConcepto(''); setMovReferencia('')
    try {
      const data = await api.get<{ movimientos: MovimientoTesoreria[] }>(`/api/tesoreria/cuentas/${c.id}`)
      setMovsCuenta(data.movimientos)
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function agregarMovimiento() {
    if (abiertaId === null || !movMonto || !movConcepto.trim()) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/tesoreria/cuentas/${abiertaId}/movimiento`, {
        tipo: movTipo, monto: Number(movMonto), concepto: movConcepto, fecha: todayIso(), referencia: movReferencia,
      })
      const data = await api.get<{ movimientos: MovimientoTesoreria[] }>(`/api/tesoreria/cuentas/${abiertaId}`)
      setMovsCuenta(data.movimientos)
      setMovMonto(''); setMovConcepto(''); setMovReferencia('')
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function eliminarMovimiento(mid: number) {
    if (!window.confirm('¿Eliminar este movimiento?')) return
    setError(null)
    try {
      await api.del(`/api/tesoreria/movimientos/${mid}`)
      if (abiertaId !== null) {
        const data = await api.get<{ movimientos: MovimientoTesoreria[] }>(`/api/tesoreria/cuentas/${abiertaId}`)
        setMovsCuenta(data.movimientos)
      }
      await load()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function transferir() {
    setTransfiriendo(true)
    setError(null)
    try {
      await api.post('/api/tesoreria/transferencia', {
        cuenta_origen_id: Number(tOrigen), cuenta_destino_id: Number(tDestino),
        monto: Number(tMonto), fecha: todayIso(), concepto: tConcepto,
      })
      setTMonto('')
      await load()
      if (abiertaId !== null) abrir(cuentas.find((c) => c.id === abiertaId)!)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setTransfiriendo(false)
    }
  }

  const columns = useMemo<ColumnDef<CuentaTesoreria>[]>(() => [
    { accessorKey: 'nombre', header: sortableHeader('Nombre'), cell: ({ row }) => <span className="font-medium">{row.original.nombre}</span> },
    { accessorKey: 'tipo', header: 'Tipo', cell: ({ row }) => TIPOS_CUENTA_TESORERIA.find((t) => t.value === row.original.tipo)?.label ?? row.original.tipo },
    {
      accessorKey: 'banco',
      header: 'Banco / N°',
      cell: ({ row }) => (
        <div className="text-sm">
          <div>{row.original.banco || '—'}</div>
          {row.original.numero && <div className="font-mono text-xs text-muted-foreground">{row.original.numero}</div>}
        </div>
      ),
    },
    { accessorKey: 'descripcion', header: 'Descripción', cell: ({ row }) => <span className="text-muted-foreground">{row.original.descripcion || '—'}</span> },
    { accessorKey: 'saldo', header: 'Saldo', cell: ({ row }) => <span className={row.original.saldo >= 0 ? 'font-medium text-emerald-600 dark:text-emerald-400' : 'font-medium text-destructive'}>{formatCurrency(row.original.saldo)}</span> },
    {
      accessorKey: 'activa',
      header: 'Estado',
      cell: ({ row }) => <Badge variant={row.original.activa ? 'default' : 'outline'}>{row.original.activa ? 'Activa' : 'Archivada'}</Badge>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => abrir(row.original)}>{abiertaId === row.original.id ? <><EyeOff />Ocultar</> : <><List />Movimientos</>}</Button>
          <Button size="sm" variant="outline" onClick={() => startEdit(row.original)}><Pencil />Editar</Button>
          <Button size="sm" variant="outline" onClick={() => eliminarCuenta(row.original)}><Trash2 />Archivar</Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [abiertaId])

  const movColumns = useMemo<ColumnDef<MovimientoTesoreria>[]>(() => [
    { accessorKey: 'fecha', header: 'Fecha' },
    { accessorKey: 'tipo', header: 'Tipo', cell: ({ row }) => <MovTipoBadge m={row.original} /> },
    { accessorKey: 'concepto', header: 'Concepto' },
    {
      accessorKey: 'monto',
      header: 'Monto',
      cell: ({ row }) => {
        const positivo = row.original.tipo === 'ingreso' || row.original.tipo === 'transferencia_entrada'
        return <span className={positivo ? 'font-medium text-emerald-600 dark:text-emerald-400' : 'font-medium text-destructive'}>{positivo ? '+' : '−'} {formatCurrency(row.original.monto)}</span>
      },
    },
    { accessorKey: 'referencia', header: 'Referencia', cell: ({ row }) => row.original.referencia || '—' },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => <Button size="sm" variant="ghost" onClick={() => eliminarMovimiento(row.original.id)}><Trash2 />Eliminar</Button>,
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  const movGeneralColumns = useMemo<ColumnDef<MovimientoTesoreria>[]>(() => [
    { accessorKey: 'fecha', header: 'Fecha' },
    { accessorKey: 'cuenta_nombre', header: 'Cuenta' },
    { accessorKey: 'tipo', header: 'Tipo', cell: ({ row }) => <MovTipoBadge m={row.original} /> },
    { accessorKey: 'concepto', header: 'Concepto' },
    {
      accessorKey: 'monto',
      header: 'Monto',
      cell: ({ row }) => {
        const positivo = row.original.tipo === 'ingreso' || row.original.tipo === 'transferencia_entrada'
        return <span className={positivo ? 'font-medium text-emerald-600 dark:text-emerald-400' : 'font-medium text-destructive'}>{positivo ? '+' : '−'} {formatCurrency(row.original.monto)}</span>
      },
    },
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Landmark className="size-5 text-primary" />Tesorería</h2>
        <span className="text-sm text-muted-foreground">Saldo total: <span className="font-medium text-foreground">{formatCurrency(totalGeneral)}</span></span>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex items-center justify-end">
        {editingId === null && <Button onClick={startCreate}><Plus />Nueva cuenta</Button>}
      </div>

      {editingId !== null && (
        <Card>
          <CardHeader><CardTitle className="text-base">{editingId === 'new' ? 'Nueva cuenta' : 'Editar cuenta'}</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5"><Label>Nombre</Label><Input value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} className="w-48" /></div>
            <div className="grid gap-1.5">
              <Label>Tipo</Label>
              <Select value={form.tipo} onValueChange={(v) => setForm({ ...form, tipo: v })}>
                <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TIPOS_CUENTA_TESORERIA.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5"><Label>Banco</Label><Input value={form.banco} onChange={(e) => setForm({ ...form, banco: e.target.value })} className="w-40" /></div>
            <div className="grid gap-1.5"><Label>Número</Label><Input value={form.numero} onChange={(e) => setForm({ ...form, numero: e.target.value })} className="w-40" /></div>
            <div className="grid gap-1.5"><Label>Saldo inicial</Label><Input type="number" step="0.01" value={form.saldo_inicial} onChange={(e) => setForm({ ...form, saldo_inicial: e.target.value })} className="w-32" /></div>
            <div className="grid gap-1.5 w-full"><Label>Descripción</Label><Input value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} /></div>
            <Button disabled={saving} onClick={guardarCuenta}><Check />{saving ? 'Guardando…' : editingId === 'new' ? 'Crear' : 'Guardar'}</Button>
            <Button type="button" variant="outline" onClick={() => setEditingId(null)}>Cancelar</Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={cuentas} emptyMessage="Sin cuentas todavía." />
          )}
        </CardContent>
      </Card>

      {abiertaId !== null && (
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-base"><List className="size-4" />Movimientos — {cuentas.find((c) => c.id === abiertaId)?.nombre}</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            <DataTable columns={movColumns} data={movsCuenta} emptyMessage="Sin movimientos." />
            <div className="flex flex-wrap items-end gap-3 border-t pt-4">
              <div className="grid gap-1.5">
                <Label>Tipo</Label>
                <Select value={movTipo} onValueChange={setMovTipo}>
                  <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ingreso"><ArrowDownCircle />Ingreso</SelectItem>
                    <SelectItem value="egreso"><ArrowUpCircle />Egreso</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5"><Label>Monto</Label><Input type="number" step="0.01" value={movMonto} onChange={(e) => setMovMonto(e.target.value)} className="w-32" /></div>
              <div className="grid gap-1.5"><Label>Concepto</Label><Input value={movConcepto} onChange={(e) => setMovConcepto(e.target.value)} className="w-52" placeholder="Ej: Cobro cliente, Pago proveedor, Retiro…" /></div>
              <div className="grid gap-1.5"><Label>Referencia</Label><Input value={movReferencia} onChange={(e) => setMovReferencia(e.target.value)} className="w-40" /></div>
              <Button disabled={saving} onClick={agregarMovimiento}><Check />{saving ? 'Guardando…' : 'Guardar'}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base"><ArrowLeftRight className="size-4" />Transferir entre cuentas</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          {cuentas.length < 2 ? (
            <p className="text-sm text-muted-foreground">Necesitás al menos dos cuentas para transferir.</p>
          ) : (
            <>
              <div className="grid gap-1.5">
                <Label>Origen</Label>
                <Select value={tOrigen} onValueChange={setTOrigen}>
                  <SelectTrigger className="w-40"><SelectValue placeholder="Cuenta…" /></SelectTrigger>
                  <SelectContent>
                    {cuentas.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre} — {formatCurrency(c.saldo)}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label>Destino</Label>
                <Select value={tDestino} onValueChange={setTDestino}>
                  <SelectTrigger className="w-40"><SelectValue placeholder="Cuenta…" /></SelectTrigger>
                  <SelectContent>
                    {cuentas.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5"><Label>Monto</Label><Input type="number" step="0.01" value={tMonto} onChange={(e) => setTMonto(e.target.value)} className="w-32" /></div>
              <div className="grid gap-1.5"><Label>Concepto</Label><Input value={tConcepto} onChange={(e) => setTConcepto(e.target.value)} className="w-52" /></div>
              <Button disabled={transfiriendo || !tOrigen || !tDestino || !tMonto} onClick={transferir}>
                <ArrowLeftRight />{transfiriendo ? 'Transfiriendo…' : 'Transferir'}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Últimos movimientos (todas las cuentas)</CardTitle></CardHeader>
        <CardContent>
          <DataTable columns={movGeneralColumns} data={movimientos} emptyMessage="Sin movimientos todavía." />
        </CardContent>
      </Card>
    </div>
  )
}
