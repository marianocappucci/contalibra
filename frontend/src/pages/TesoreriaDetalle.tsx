import { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import {
  api, ApiError, TIPOS_CUENTA_TESORERIA, type CuentaTesoreria, type MovimientoTesoreria,
} from '../api'
import { MovTipoBadge } from './Tesoreria'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger, DialogClose,
} from '@/components/ui/dialog'
import { DataTable } from '@/components/data-table'
import {
  ArrowLeft, ArrowLeftRight, Check, Landmark, Pencil, Plus, Trash2,
} from 'lucide-react'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

export function TesoreriaDetalle() {
  const { id } = useParams<{ id: string }>()
  const cuentaId = Number(id)

  const [cuenta, setCuenta] = useState<CuentaTesoreria | null>(null)
  const [movimientos, setMovimientos] = useState<MovimientoTesoreria[]>([])
  const [todas, setTodas] = useState<CuentaTesoreria[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')

  const [movOpen, setMovOpen] = useState(false)
  const [movTipo, setMovTipo] = useState('ingreso')
  const [movMonto, setMovMonto] = useState('')
  const [movFecha, setMovFecha] = useState(todayIso())
  const [movConcepto, setMovConcepto] = useState('')
  const [movReferencia, setMovReferencia] = useState('')
  const [saving, setSaving] = useState(false)

  const [transferOpen, setTransferOpen] = useState(false)
  const [tDestino, setTDestino] = useState('')
  const [tMonto, setTMonto] = useState('')
  const [tFecha, setTFecha] = useState(todayIso())
  const [tConcepto, setTConcepto] = useState('Transferencia entre cuentas')
  const [tReferencia, setTReferencia] = useState('')
  const [transfiriendo, setTransfiriendo] = useState(false)

  useEffect(() => {
    cargar()
    api.get<{ cuentas: CuentaTesoreria[] }>('/api/tesoreria').then((d) => setTodas(d.cuentas.filter((c) => c.id !== cuentaId))).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cuentaId])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function cargar() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ cuenta: CuentaTesoreria; movimientos: MovimientoTesoreria[] }>(
        `/api/tesoreria/cuentas/${cuentaId}?desde=${desde}&hasta=${hasta}`,
      )
      setCuenta(data.cuenta)
      setMovimientos(data.movimientos)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  function abrirMovimiento() {
    setMovTipo('ingreso'); setMovMonto(''); setMovFecha(todayIso()); setMovConcepto(''); setMovReferencia('')
    setMovOpen(true)
  }

  async function agregarMovimiento() {
    if (!movMonto || !movConcepto.trim()) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/tesoreria/cuentas/${cuentaId}/movimiento`, {
        tipo: movTipo, monto: Number(movMonto), concepto: movConcepto, fecha: movFecha, referencia: movReferencia,
      })
      setMovOpen(false)
      await cargar()
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
      await cargar()
    } catch (err) {
      setError(describeError(err))
    }
  }

  function abrirTransfer() {
    setTDestino(''); setTMonto(''); setTFecha(todayIso())
    setTConcepto('Transferencia entre cuentas'); setTReferencia('')
    setTransferOpen(true)
  }

  async function transferir() {
    if (!cuenta || !tDestino || !tMonto) return
    setTransfiriendo(true)
    setError(null)
    try {
      await api.post('/api/tesoreria/transferencia', {
        cuenta_origen_id: cuenta.id, cuenta_destino_id: Number(tDestino),
        monto: Number(tMonto), fecha: tFecha, concepto: tConcepto, referencia: tReferencia,
      })
      setTransferOpen(false)
      await cargar()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setTransfiriendo(false)
    }
  }

  function filtrar() {
    cargar()
  }

  function limpiarFiltros() {
    setDesde(''); setHasta('')
    setTimeout(cargar, 0)
  }

  const movColumns = useMemo<ColumnDef<MovimientoTesoreria>[]>(() => [
    { accessorKey: 'fecha', header: 'Fecha' },
    { accessorKey: 'tipo', header: 'Tipo', cell: ({ row }) => <MovTipoBadge m={row.original} /> },
    { accessorKey: 'concepto', header: 'Concepto' },
    { accessorKey: 'usuario_nombre', header: 'Usuario', cell: ({ row }) => row.original.usuario_nombre || '—' },
    { accessorKey: 'referencia', header: 'Referencia', cell: ({ row }) => row.original.referencia || '' },
    {
      accessorKey: 'monto',
      header: () => <div className="text-right">Monto</div>,
      cell: ({ row }) => {
        const positivo = row.original.tipo === 'ingreso' || row.original.tipo === 'transferencia_entrada'
        return <div className={`text-right font-semibold ${positivo ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}`}>{positivo ? '+' : '−'} {formatCurrency(row.original.monto)}</div>
      },
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => <Button size="sm" variant="ghost" onClick={() => eliminarMovimiento(row.original.id)}><Trash2 />Eliminar</Button>,
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Landmark className="size-5 text-primary" />
          {cuenta ? cuenta.nombre : 'Cuenta'}
          {cuenta && (
            <Badge className={cuenta.saldo >= 0 ? 'bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15 dark:text-emerald-400' : ''} variant={cuenta.saldo >= 0 ? undefined : 'destructive'}>
              {formatCurrency(cuenta.saldo)}
            </Badge>
          )}
        </h2>
        {cuenta && (
          <div className="flex flex-wrap gap-2">
            {todas.length > 0 && (
              <Dialog open={transferOpen} onOpenChange={setTransferOpen}>
                <DialogTrigger asChild>
                  <Button size="sm" variant="outline" onClick={abrirTransfer}><ArrowLeftRight />Transferir</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2"><ArrowLeftRight className="size-4" />Transferir desde {cuenta.nombre}</DialogTitle>
                  </DialogHeader>
                  <div className="grid gap-3">
                    <div className="grid gap-1.5">
                      <Label>Cuenta destino</Label>
                      <Select value={tDestino} onValueChange={setTDestino}>
                        <SelectTrigger><SelectValue placeholder="Cuenta…" /></SelectTrigger>
                        <SelectContent>
                          {todas.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.nombre} — {formatCurrency(c.saldo)}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="grid gap-1.5"><Label>Monto</Label><Input type="number" step="0.01" min="0.01" value={tMonto} onChange={(e) => setTMonto(e.target.value)} /></div>
                      <div className="grid gap-1.5"><Label>Fecha</Label><Input type="date" value={tFecha} onChange={(e) => setTFecha(e.target.value)} /></div>
                    </div>
                    <div className="grid gap-1.5"><Label>Concepto</Label><Input value={tConcepto} onChange={(e) => setTConcepto(e.target.value)} /></div>
                    <div className="grid gap-1.5">
                      <Label>Referencia <span className="font-normal text-muted-foreground">(opcional)</span></Label>
                      <Input value={tReferencia} onChange={(e) => setTReferencia(e.target.value)} placeholder="N° op., comprobante…" />
                    </div>
                  </div>
                  <DialogFooter>
                    <DialogClose asChild><Button type="button" variant="outline">Cancelar</Button></DialogClose>
                    <Button disabled={transfiriendo || !tDestino || !tMonto} onClick={transferir}>
                      <ArrowLeftRight />{transfiriendo ? 'Transfiriendo…' : 'Transferir'}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            )}
            <Dialog open={movOpen} onOpenChange={setMovOpen}>
              <DialogTrigger asChild>
                <Button size="sm" className="bg-emerald-600 text-white hover:bg-emerald-600/90" onClick={abrirMovimiento}>
                  <Plus />Movimiento
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2"><Plus className="size-4" />Registrar movimiento</DialogTitle>
                </DialogHeader>
                <div className="grid gap-3">
                  <div className="grid gap-1.5">
                    <Label>Tipo</Label>
                    <div className="grid grid-cols-2 gap-2">
                      <Button type="button" variant={movTipo === 'ingreso' ? 'default' : 'outline'} onClick={() => setMovTipo('ingreso')}>Ingreso</Button>
                      <Button type="button" variant={movTipo === 'egreso' ? 'default' : 'outline'} onClick={() => setMovTipo('egreso')}>Egreso</Button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="grid gap-1.5"><Label>Monto</Label><Input type="number" step="0.01" min="0.01" value={movMonto} onChange={(e) => setMovMonto(e.target.value)} /></div>
                    <div className="grid gap-1.5"><Label>Fecha</Label><Input type="date" value={movFecha} onChange={(e) => setMovFecha(e.target.value)} /></div>
                  </div>
                  <div className="grid gap-1.5">
                    <Label>Concepto <span className="text-destructive">*</span></Label>
                    <Input value={movConcepto} onChange={(e) => setMovConcepto(e.target.value)} placeholder="Ej: Cobro cliente, Pago proveedor, Retiro…" />
                  </div>
                  <div className="grid gap-1.5">
                    <Label>Referencia <span className="font-normal text-muted-foreground">(opcional)</span></Label>
                    <Input value={movReferencia} onChange={(e) => setMovReferencia(e.target.value)} placeholder="N° cheque, transferencia, etc." />
                  </div>
                </div>
                <DialogFooter>
                  <DialogClose asChild><Button type="button" variant="outline">Cancelar</Button></DialogClose>
                  <Button disabled={saving || !movMonto || !movConcepto.trim()} onClick={agregarMovimiento}>
                    <Check />{saving ? 'Guardando…' : 'Guardar'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <Button asChild size="sm" variant="outline"><Link to={`/tesoreria/${cuenta.id}/editar`}><Pencil />Editar</Link></Button>
            <Button asChild size="sm" variant="outline"><Link to="/tesoreria"><ArrowLeft />Volver</Link></Button>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading || !cuenta ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">Tipo</p>
                <p className="font-semibold">{TIPOS_CUENTA_TESORERIA.find((t) => t.value === cuenta.tipo)?.label ?? cuenta.tipo}</p>
                {cuenta.banco && <p className="mt-1 text-sm text-muted-foreground">{cuenta.banco}</p>}
                {cuenta.numero && <p className="font-mono text-sm text-muted-foreground">{cuenta.numero}</p>}
                {cuenta.descripcion && <p className="mt-1 text-sm text-muted-foreground">{cuenta.descripcion}</p>}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-3 text-center">
                <p className="text-sm text-muted-foreground">Saldo inicial</p>
                <p className="text-lg font-semibold">{formatCurrency(cuenta.saldo_inicial)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-3 text-center">
                <p className="text-sm text-muted-foreground">Saldo actual</p>
                <p className={`text-xl font-bold ${cuenta.saldo >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}`}>{formatCurrency(cuenta.saldo)}</p>
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-wrap items-end gap-2">
            <div className="grid gap-1.5"><Label className="text-xs">Desde</Label><Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="h-8 w-40" /></div>
            <div className="grid gap-1.5"><Label className="text-xs">Hasta</Label><Input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="h-8 w-40" /></div>
            <Button size="sm" variant="outline" onClick={filtrar}>Filtrar</Button>
            {(desde || hasta) && <Button size="sm" variant="outline" onClick={limpiarFiltros}>Limpiar</Button>}
          </div>

          <Card>
            <CardHeader><CardTitle className="text-base">Movimientos</CardTitle></CardHeader>
            <CardContent>
              <DataTable columns={movColumns} data={movimientos} emptyMessage="No hay movimientos registrados." />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
