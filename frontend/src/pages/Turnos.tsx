import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, MEDIOS_PAGO_LABELS, type ResumenTurno, type Turno } from '../api'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { DataTable, sortableHeader } from '@/components/data-table'
import {
  Clock, PlayCircle, StopCircle, Eye, ArrowUpCircle, ArrowDownCircle, CheckCircle2, Receipt,
} from 'lucide-react'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

function DiferenciaBadge({ esperado, declarado }: { esperado: number | null; declarado: number | null }) {
  if (esperado === null || declarado === null) return <span className="text-muted-foreground">—</span>
  const dif = Math.round((declarado - esperado) * 100) / 100
  if (dif > 0.01) {
    return <span className="inline-flex items-center gap-1 font-medium text-emerald-600 dark:text-emerald-400"><ArrowUpCircle className="size-4" />+{formatCurrency(dif)}</span>
  }
  if (dif < -0.01) {
    return <span className="inline-flex items-center gap-1 font-medium text-destructive"><ArrowDownCircle className="size-4" />−{formatCurrency(Math.abs(dif))}</span>
  }
  return <span className="inline-flex items-center gap-1 text-muted-foreground"><CheckCircle2 className="size-4" />OK</span>
}

const estadoVentaVariant: Record<string, 'default' | 'destructive'> = { cobrada: 'default', anulada: 'destructive' }

export function Turnos() {
  const { user } = useAuth()
  const esAdmin = user?.role === 'admin'
  const [turnos, setTurnos] = useState<Turno[]>([])
  const [turnoActivo, setTurnoActivo] = useState<Turno | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [abriendo, setAbriendo] = useState(false)
  const [montoInicial, setMontoInicial] = useState('0')
  const [notasApertura, setNotasApertura] = useState('')

  const [abiertoId, setAbiertoId] = useState<number | null>(null)
  const [resumen, setResumen] = useState<ResumenTurno | null>(null)
  const [cerrando, setCerrando] = useState(false)
  const [montoDeclarado, setMontoDeclarado] = useState('')
  const [notasCierre, setNotasCierre] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => { load() }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ turnos: Turno[]; turno_activo: Turno | null }>('/api/turnos')
      setTurnos(data.turnos)
      setTurnoActivo(data.turno_activo)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function abrirTurno() {
    setSaving(true)
    setError(null)
    try {
      await api.post('/api/turnos/abrir', { monto_inicial: Number(montoInicial) || 0, notas: notasApertura })
      setAbriendo(false)
      setMontoInicial('0'); setNotasApertura('')
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function verDetalle(t: Turno) {
    if (abiertoId === t.id) {
      setAbiertoId(null)
      return
    }
    setAbiertoId(t.id)
    setCerrando(false)
    setError(null)
    try {
      const data = await api.get<{ turno: Turno; resumen: ResumenTurno }>(`/api/turnos/${t.id}`)
      setResumen(data.resumen)
      setMontoDeclarado(String(Math.round((t.monto_inicial + data.resumen.efectivo_ventas) * 100) / 100))
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function cerrarTurno(tid: number) {
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/turnos/${tid}/cerrar`, { monto_declarado: Number(montoDeclarado) || 0, notas: notasCierre })
      setAbiertoId(null)
      setCerrando(false)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  const columns = useMemo<ColumnDef<Turno>[]>(() => {
    const cols: ColumnDef<Turno>[] = [
      { accessorKey: 'id', header: 'N°', cell: ({ row }) => <span className="text-sm text-muted-foreground">{row.original.id}</span> },
    ]
    if (esAdmin) {
      cols.push({ accessorKey: 'usuario_nombre', header: sortableHeader('Cajero'), cell: ({ row }) => <span className="font-medium">{row.original.usuario_nombre}</span> })
    }
    cols.push(
      { accessorKey: 'apertura', header: 'Apertura' },
      { accessorKey: 'cierre', header: 'Cierre', cell: ({ row }) => row.original.cierre || '—' },
      { accessorKey: 'monto_inicial', header: 'Fondo inicial', cell: ({ row }) => formatCurrency(row.original.monto_inicial) },
      { accessorKey: 'monto_esperado_cierre', header: 'Efectivo esperado', cell: ({ row }) => row.original.monto_esperado_cierre != null ? formatCurrency(row.original.monto_esperado_cierre) : '—' },
      { accessorKey: 'monto_declarado_cierre', header: 'Efectivo declarado', cell: ({ row }) => row.original.monto_declarado_cierre != null ? formatCurrency(row.original.monto_declarado_cierre) : '—' },
      {
        id: 'diferencia',
        header: 'Diferencia',
        cell: ({ row }) => <DiferenciaBadge esperado={row.original.monto_esperado_cierre} declarado={row.original.monto_declarado_cierre} />,
      },
      {
        accessorKey: 'estado',
        header: 'Estado',
        cell: ({ row }) => <Badge variant={row.original.estado === 'abierto' ? 'default' : 'secondary'}>{row.original.estado === 'abierto' ? 'Abierto' : 'Cerrado'}</Badge>,
      },
      {
        id: 'actions',
        header: () => <div className="text-right">Acciones</div>,
        cell: ({ row }) => (
          <div className="flex justify-end">
            <Button size="sm" variant="outline" onClick={() => verDetalle(row.original)}>
              <Eye />{abiertoId === row.original.id ? 'Ocultar' : 'Ver detalle'}
            </Button>
          </div>
        ),
      },
    )
    return cols
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abiertoId, esAdmin])

  const turnoSeleccionado = turnos.find((t) => t.id === abiertoId)

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold"><Clock className="size-5" />Turnos de caja</h2>
        {!turnoActivo && !abriendo && <Button onClick={() => setAbriendo(true)}><PlayCircle />Abrir turno</Button>}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {turnoActivo && (
        <Card className="border-emerald-600/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <span className="inline-block size-2.5 rounded-full bg-emerald-500" />Turno abierto
            </CardTitle>
            <CardDescription>Desde {turnoActivo.apertura} — fondo inicial {formatCurrency(turnoActivo.monto_inicial)}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => verDetalle(turnoActivo)}><Eye />Ver detalle</Button>
            <Button size="sm" variant="destructive" onClick={() => { verDetalle(turnoActivo).then(() => setCerrando(true)) }}><StopCircle />Cerrar turno</Button>
          </CardContent>
        </Card>
      )}

      {abriendo && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base"><PlayCircle className="size-4 text-emerald-600" />Abrir turno</CardTitle>
            <CardDescription>Registrá el efectivo en caja al inicio del turno. Se usa para calcular la diferencia al cierre.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5"><Label>Fondo inicial</Label><Input type="number" step="0.01" value={montoInicial} onChange={(e) => setMontoInicial(e.target.value)} className="w-32" /></div>
            <div className="grid gap-1.5"><Label>Notas</Label><Input value={notasApertura} onChange={(e) => setNotasApertura(e.target.value)} className="w-52" /></div>
            <Button disabled={saving} onClick={abrirTurno}><PlayCircle />{saving ? 'Abriendo…' : 'Abrir turno ahora'}</Button>
            <Button type="button" variant="outline" onClick={() => setAbriendo(false)}>Cancelar</Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle className="text-base">{esAdmin ? 'Todos los turnos' : 'Mis turnos'}</CardTitle></CardHeader>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={turnos} emptyMessage="No hay turnos registrados." />
          )}
        </CardContent>
      </Card>

      {abiertoId !== null && resumen && turnoSeleccionado && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader><CardTitle className="text-base">Datos del turno</CardTitle></CardHeader>
            <CardContent className="grid gap-1.5 text-sm">
              <p><span className="text-muted-foreground">Cajero:</span> {turnoSeleccionado.usuario_nombre}</p>
              <p><span className="text-muted-foreground">Apertura:</span> {turnoSeleccionado.apertura}</p>
              {turnoSeleccionado.cierre && <p><span className="text-muted-foreground">Cierre:</span> {turnoSeleccionado.cierre}</p>}
              <p><span className="text-muted-foreground">Fondo inicial:</span> {formatCurrency(turnoSeleccionado.monto_inicial)}</p>
              {turnoSeleccionado.notas && <p><span className="text-muted-foreground">Notas:</span> {turnoSeleccionado.notas}</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Recaudación por medio</CardTitle></CardHeader>
            <CardContent className="grid gap-1.5 text-sm">
              {Object.keys(resumen.pagos_por_medio).length === 0 ? (
                <p className="text-muted-foreground">Sin ventas en este turno.</p>
              ) : (
                <>
                  {Object.entries(resumen.pagos_por_medio).map(([medio, total]) => (
                    <div key={medio} className="flex justify-between">
                      <Badge variant="outline">{MEDIOS_PAGO_LABELS[medio] ?? medio}</Badge>
                      <span className="font-medium">{formatCurrency(total)}</span>
                    </div>
                  ))}
                  <div className="mt-1 flex justify-between border-t pt-1.5 font-semibold">
                    <span>Total</span><span>{formatCurrency(resumen.total_ventas)}</span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {turnoSeleccionado.estado === 'cerrado' && turnoSeleccionado.monto_declarado_cierre != null && turnoSeleccionado.monto_esperado_cierre != null && (
            <Card>
              <CardHeader><CardTitle className="text-base">Resultado del cierre</CardTitle></CardHeader>
              <CardContent className="grid gap-1.5 text-sm">
                <p><span className="text-muted-foreground">Efectivo esperado:</span> {formatCurrency(turnoSeleccionado.monto_esperado_cierre)}</p>
                <p><span className="text-muted-foreground">Efectivo declarado:</span> {formatCurrency(turnoSeleccionado.monto_declarado_cierre)}</p>
                <div className="mt-1 flex items-center gap-2 border-t pt-1.5 font-semibold">
                  <span>Diferencia:</span>
                  <DiferenciaBadge esperado={turnoSeleccionado.monto_esperado_cierre} declarado={turnoSeleccionado.monto_declarado_cierre} />
                </div>
              </CardContent>
            </Card>
          )}

          <Card className="md:col-span-2">
            <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Receipt className="size-4" />Ventas del turno<Badge variant="outline">{resumen.ventas.length}</Badge></CardTitle></CardHeader>
            <CardContent className="p-0">
              {resumen.ventas.length === 0 ? (
                <p className="p-4 text-center text-sm text-muted-foreground">No hay ventas en este turno todavía.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead className="border-b text-muted-foreground">
                    <tr>
                      <th className="p-3 text-left font-medium">N°</th>
                      <th className="p-3 text-left font-medium">Fecha/Hora</th>
                      <th className="p-3 text-left font-medium">Cliente</th>
                      <th className="p-3 text-right font-medium">Total</th>
                      <th className="p-3 text-center font-medium">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resumen.ventas.map((v) => (
                      <tr key={v.id} className="border-b last:border-0">
                        <td className="p-3"><a href={`/ventas?ver=${v.id}`} className="font-mono font-medium text-primary hover:underline">{v.numero}</a></td>
                        <td className="p-3 text-muted-foreground">{v.fecha}</td>
                        <td className="p-3">{v.cliente_nombre || '— Consumidor final —'}</td>
                        <td className="p-3 text-right font-medium">{formatCurrency(v.total)}</td>
                        <td className="p-3 text-center"><Badge variant={estadoVentaVariant[v.estado] ?? 'outline'}>{v.estado === 'cobrada' ? 'Cobrada' : v.estado === 'anulada' ? 'Anulada' : v.estado}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>

          {turnoSeleccionado.estado === 'abierto' && (
            <Card className="md:col-span-2">
              <CardHeader><CardTitle className="text-base">Cerrar turno</CardTitle></CardHeader>
              <CardContent className="grid gap-3">
                {!cerrando ? (
                  <Button variant="destructive" className="w-fit" onClick={() => setCerrando(true)}><StopCircle />Cerrar turno</Button>
                ) : (
                  <>
                    <div className="flex flex-wrap items-end gap-3">
                      <div className="grid gap-1.5"><Label>Efectivo contado en caja</Label><Input type="number" step="0.01" value={montoDeclarado} onChange={(e) => setMontoDeclarado(e.target.value)} className="w-36" /></div>
                      <div className="grid gap-1.5"><Label>Notas de cierre</Label><Input value={notasCierre} onChange={(e) => setNotasCierre(e.target.value)} className="w-52" /></div>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Diferencia estimada:</span>
                      <DiferenciaBadge
                        esperado={turnoSeleccionado.monto_inicial + resumen.efectivo_ventas}
                        declarado={Number(montoDeclarado) || 0}
                      />
                      <span className="text-muted-foreground">(esperado: {formatCurrency(turnoSeleccionado.monto_inicial + resumen.efectivo_ventas)})</span>
                    </div>
                    <div className="flex gap-2">
                      <Button disabled={saving} onClick={() => cerrarTurno(abiertoId)}><StopCircle />{saving ? 'Cerrando…' : 'Confirmar cierre de turno'}</Button>
                      <Button type="button" variant="outline" onClick={() => setCerrando(false)}>Cancelar</Button>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
