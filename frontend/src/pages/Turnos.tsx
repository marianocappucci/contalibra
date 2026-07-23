import { useEffect, useMemo, useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, MEDIOS_PAGO_LABELS, type ResumenTurno, type Turno } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { DataTable, sortableHeader } from '@/components/data-table'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

export function Turnos() {
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

  const columns = useMemo<ColumnDef<Turno>[]>(() => [
    { accessorKey: 'usuario_nombre', header: sortableHeader('Usuario') },
    { accessorKey: 'apertura', header: 'Apertura' },
    { accessorKey: 'cierre', header: 'Cierre', cell: ({ row }) => row.original.cierre || '—' },
    { accessorKey: 'monto_inicial', header: 'Fondo inicial', cell: ({ row }) => formatCurrency(row.original.monto_inicial) },
    {
      accessorKey: 'estado',
      header: 'Estado',
      cell: ({ row }) => <Badge variant={row.original.estado === 'abierto' ? 'default' : 'outline'}>{row.original.estado}</Badge>,
    },
    {
      id: 'actions',
      header: () => <div className="text-right">Acciones</div>,
      cell: ({ row }) => (
        <div className="flex justify-end">
          <Button size="sm" variant="outline" onClick={() => verDetalle(row.original)}>
            {abiertoId === row.original.id ? 'Ocultar' : 'Ver detalle'}
          </Button>
        </div>
      ),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [abiertoId])

  const turnoSeleccionado = turnos.find((t) => t.id === abiertoId)

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Turnos de caja</h2>
        {!turnoActivo && !abriendo && <Button onClick={() => setAbriendo(true)}>Abrir turno</Button>}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {turnoActivo && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Turno activo</CardTitle>
            <CardDescription>Abierto {turnoActivo.apertura} — fondo inicial {formatCurrency(turnoActivo.monto_inicial)}</CardDescription>
          </CardHeader>
        </Card>
      )}

      {abriendo && (
        <Card>
          <CardHeader><CardTitle className="text-base">Abrir turno</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5"><Label>Fondo inicial</Label><Input type="number" step="0.01" value={montoInicial} onChange={(e) => setMontoInicial(e.target.value)} className="w-32" /></div>
            <div className="grid gap-1.5"><Label>Notas</Label><Input value={notasApertura} onChange={(e) => setNotasApertura(e.target.value)} className="w-52" /></div>
            <Button disabled={saving} onClick={abrirTurno}>{saving ? 'Abriendo…' : 'Abrir'}</Button>
            <Button type="button" variant="outline" onClick={() => setAbriendo(false)}>Cancelar</Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DataTable columns={columns} data={turnos} emptyMessage="Sin turnos todavía." />
          )}
        </CardContent>
      </Card>

      {abiertoId !== null && resumen && (
        <Card>
          <CardHeader><CardTitle className="text-base">Resumen del turno</CardTitle></CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-1 text-sm">
              <p>Total ventas: <span className="font-medium">{formatCurrency(resumen.total_ventas)}</span></p>
              <p>Ventas en efectivo: <span className="font-medium">{formatCurrency(resumen.efectivo_ventas)}</span></p>
              {Object.entries(resumen.pagos_por_medio).map(([medio, total]) => (
                <p key={medio} className="text-muted-foreground">{MEDIOS_PAGO_LABELS[medio] ?? medio}: {formatCurrency(total)}</p>
              ))}
            </div>
            {turnoSeleccionado?.estado === 'abierto' && (
              cerrando ? (
                <div className="flex flex-wrap items-end gap-3 border-t pt-4">
                  <div className="grid gap-1.5"><Label>Monto declarado</Label><Input type="number" step="0.01" value={montoDeclarado} onChange={(e) => setMontoDeclarado(e.target.value)} className="w-32" /></div>
                  <div className="grid gap-1.5"><Label>Notas</Label><Input value={notasCierre} onChange={(e) => setNotasCierre(e.target.value)} className="w-52" /></div>
                  <Button disabled={saving} onClick={() => cerrarTurno(abiertoId)}>{saving ? 'Cerrando…' : 'Confirmar cierre'}</Button>
                  <Button type="button" variant="outline" onClick={() => setCerrando(false)}>Cancelar</Button>
                </div>
              ) : (
                <Button variant="outline" className="w-fit" onClick={() => setCerrando(true)}>Cerrar turno</Button>
              )
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
