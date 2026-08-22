import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { type ColumnDef } from '@tanstack/react-table'
import { api, ApiError, type ComprobantePendiente, type PrefillComprobantes } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BadgeEstado } from 'libra-ui/badge-estado'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DataTable, sortableHeader } from 'libra-ui/data-table'
import {
  Inbox, ReceiptText, X, Package, Wrench, FileText, FileSpreadsheet, Info,
} from 'lucide-react'
import { TituloPantalla } from 'libra-ui/titulo-pantalla'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

type Bandeja = {
  pendientes: ComprobantePendiente[]
  facturados: ComprobantePendiente[]
  descartados: ComprobantePendiente[]
  total_pendientes: number
}

// El origen se muestra con etiqueta propia y no con el string crudo: lo manda
// otro sistema y "cuota_contrato" no significa nada para quien mira la
// bandeja.
const ORIGENES: Record<string, { label: string; icon: typeof Package }> = {
  cuota_contrato: { label: 'Cuota de contrato', icon: Package },
  incidencia: { label: 'Ticket', icon: Wrench },
  remito: { label: 'Remito', icon: FileText },
  presupuesto: { label: 'Presupuesto', icon: FileSpreadsheet },
}

function OrigenBadge({ tipo, producto }: { tipo: string; producto: string }) {
  const conf = ORIGENES[tipo] ?? { label: tipo, icon: FileText }
  const Icon = conf.icon
  return (
    <span className="inline-flex items-center gap-1.5" title={`Enviado por ${producto}`}>
      <Icon className="size-3.5 shrink-0 text-muted-foreground" />
      <span className="truncate">{conf.label}</span>
    </span>
  )
}

function periodo(c: ComprobantePendiente): string {
  if (!c.periodo_desde && !c.periodo_hasta) return '—'
  if (c.periodo_desde === c.periodo_hasta) return c.periodo_desde
  return `${c.periodo_desde || '—'} → ${c.periodo_hasta || '—'}`
}

export function ComprobantesPendientes() {
  const navigate = useNavigate()
  const [data, setData] = useState<Bandeja | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<'pendientes' | 'facturados' | 'descartados'>('pendientes')
  const [elegidos, setElegidos] = useState<number[]>([])
  const [descartando, setDescartando] = useState<ComprobantePendiente | null>(null)
  const [motivo, setMotivo] = useState('')
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
      setData(await api.get<Bandeja>('/api/comprobantes-pendientes'))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  // Memoizado y no `data?.pendientes ?? []` a secas: el `??` devuelve un array
  // nuevo en cada render y los dos `useMemo` de abajo se recalcularían siempre.
  const pendientes = useMemo(() => data?.pendientes ?? [], [data])

  // Sólo se pueden facturar juntos comprobantes del mismo cliente: una factura
  // tiene un solo receptor. El backend lo rechaza igual (422), pero dejar
  // tildar lo que después va a fallar es una trampa — acá se deshabilita.
  const clienteElegido = useMemo(() => {
    const primero = pendientes.find((c) => elegidos.includes(c.id))
    return primero ? (primero.cliente_cuit || primero.cliente_razon) : null
  }, [pendientes, elegidos])

  const totalElegido = useMemo(
    () => pendientes.filter((c) => elegidos.includes(c.id)).reduce((acc, c) => acc + c.total, 0),
    [pendientes, elegidos],
  )

  async function facturar() {
    setSaving(true)
    setError(null)
    try {
      const prefill = await api.post<PrefillComprobantes>(
        '/api/comprobantes-pendientes/facturar-prefill', { ids: elegidos },
      )
      // El formulario de siempre, con todo cargado. La emisión y el CAE pasan
      // ahí, no acá: esta pantalla nunca factura por su cuenta.
      navigate('/facturas/nuevo', {
        state: {
          clienteId: prefill.client_id ? String(prefill.client_id) : '',
          clienteNombreLibre: prefill.client_id ? '' : prefill.client_name,
          concepto: String(prefill.concepto),
          condicionVenta: prefill.condicion_venta,
          taxRate: String(prefill.tax_rate),
          observations: prefill.observations,
          items: prefill.items.map((i) => ({
            description: i.description, qty: String(i.qty), unit_price: String(i.unit_price),
          })),
          fchServDesde: prefill.fch_serv_desde,
          fchServHasta: prefill.fch_serv_hasta,
          fchVtoPago: prefill.fch_vto_pago,
          comprobantesPendientesIds: prefill.comprobantes_ids,
          avisos: prefill.avisos,
        },
      })
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function confirmarDescarte() {
    if (!descartando) return
    setSaving(true)
    setError(null)
    try {
      await api.post(`/api/comprobantes-pendientes/${descartando.id}/descartar`, { motivo })
      setDescartando(null)
      setMotivo('')
      setElegidos((prev) => prev.filter((x) => x !== descartando.id))
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  const columnsPendientes = useMemo<ColumnDef<ComprobantePendiente>[]>(() => [
    {
      id: 'elegir',
      header: '',
      size: 40,
      minSize: 40,
      cell: ({ row }) => {
        const c = row.original
        // Sólo se pueden juntar comprobantes del mismo cliente. La comparación
        // va inline y no en un helper del componente para que el arreglo de
        // dependencias del memo sea el de verdad: con el helper, `elegidos` y
        // `clienteElegido` entraban por la puerta de atrás y el linter tenía
        // razón en quejarse.
        const habilitado = clienteElegido === null
          || (c.cliente_cuit || c.cliente_razon) === clienteElegido
        return (
          // Checkbox nativo, como el resto de las pantallas del producto
          // (Cajas, Recibos, ListaPrecioDetalle): no hay componente shadcn de
          // checkbox acá y agregarlo traería una dependencia de radix por una
          // sola tabla.
          <input
            type="checkbox"
            checked={elegidos.includes(c.id)}
            disabled={!habilitado}
            onChange={() => setElegidos((prev) => prev.includes(c.id)
              ? prev.filter((x) => x !== c.id)
              : [...prev, c.id])}
            aria-label={`Elegir ${c.cliente_razon}`}
            title={habilitado ? undefined : 'Es de otro cliente: una factura tiene un solo receptor'}
          />
        )
      },
    },
    {
      accessorKey: 'cliente_razon',
      header: sortableHeader('Cliente'),
      size: 180,
      minSize: 120,
      meta: { stretch: true },
      cell: ({ row }) => (
        <div className="w-full">
          <p className="truncate font-medium" title={row.original.cliente_razon}>{row.original.cliente_razon}</p>
          {row.original.cliente_cuit && <p className="truncate text-xs text-muted-foreground">{row.original.cliente_cuit}</p>}
        </div>
      ),
    },
    {
      id: 'origen',
      header: 'Origen',
      size: 150,
      minSize: 110,
      cell: ({ row }) => <OrigenBadge tipo={row.original.origen_tipo} producto={row.original.origen_producto} />,
    },
    {
      id: 'detalle',
      header: 'Detalle',
      size: 200,
      minSize: 140,
      cell: ({ row }) => {
        const items = row.original.items
        const primero = items[0]?.description ?? '—'
        const resto = items.length - 1
        return (
          <span className="block w-full truncate" title={items.map((i) => i.description).join(' · ')}>
            {primero}{resto > 0 ? ` +${resto}` : ''}
          </span>
        )
      },
    },
    { id: 'periodo', header: 'Período', size: 170, minSize: 130, cell: ({ row }) => periodo(row.original) },
    {
      accessorKey: 'total',
      header: sortableHeader('Total'),
      size: 110,
      minSize: 90,
      cell: ({ row }) => <span className="font-medium">{formatCurrency(row.original.total)}</span>,
    },
    {
      id: 'acciones',
      header: '',
      size: 60,
      minSize: 60,
      cell: ({ row }) => (
        <Button
          size="icon" variant="outline" title="Descartar"
          onClick={() => { setDescartando(row.original); setMotivo('') }}
        >
          <X className="size-4" />
        </Button>
      ),
    },
  ], [elegidos, clienteElegido])

  const columnsResueltos = useMemo<ColumnDef<ComprobantePendiente>[]>(() => [
    {
      accessorKey: 'cliente_razon',
      header: sortableHeader('Cliente'),
      size: 180,
      minSize: 120,
      meta: { stretch: true },
      cell: ({ row }) => <span className="block w-full truncate" title={row.original.cliente_razon}>{row.original.cliente_razon}</span>,
    },
    {
      id: 'origen',
      header: 'Origen',
      size: 150,
      minSize: 110,
      cell: ({ row }) => <OrigenBadge tipo={row.original.origen_tipo} producto={row.original.origen_producto} />,
    },
    {
      accessorKey: 'total',
      header: 'Total',
      size: 110,
      minSize: 90,
      cell: ({ row }) => formatCurrency(row.original.total),
    },
    { accessorKey: 'resuelto_at', header: sortableHeader('Resuelto'), size: 140, minSize: 110 },
    { accessorKey: 'resuelto_por', header: 'Por', size: 120, minSize: 90 },
    {
      id: 'resultado',
      header: 'Resultado',
      size: 150,
      minSize: 120,
      cell: ({ row }) => {
        const c = row.original
        if (c.estado === 'facturado') {
          return c.factura_id
            ? <Button asChild size="sm" variant="outline"><Link to={`/facturas/${c.factura_id}`}><ReceiptText className="mr-1 size-4" />Ver factura</Link></Button>
            : <BadgeEstado tono="ok">Facturado</BadgeEstado>
        }
        return (
          <span className="block w-full truncate text-muted-foreground" title={c.motivo_descarte || undefined}>
            {c.motivo_descarte || 'Descartado'}
          </span>
        )
      },
    },
  ], [])

  const filas = tab === 'pendientes' ? pendientes
    : tab === 'facturados' ? (data?.facturados ?? [])
      : (data?.descartados ?? [])

  return (
    <div className="grid gap-4">
      <TituloPantalla icono={Inbox}>Comprobantes a facturar</TituloPantalla>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
          <CardTitle className="text-base">
            {tab === 'pendientes' ? 'Pendientes' : tab === 'facturados' ? 'Facturados' : 'Descartados'}
          </CardTitle>
          <Tabs value={tab} onValueChange={(v) => { setTab(v as typeof tab); setElegidos([]) }}>
            <TabsList>
              <TabsTrigger value="pendientes">
                Pendientes{data ? ` (${data.total_pendientes})` : ''}
              </TabsTrigger>
              <TabsTrigger value="facturados">Facturados</TabsTrigger>
              <TabsTrigger value="descartados">Descartados</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className="grid gap-3">
          {tab === 'pendientes' && (
            <p className="flex items-start gap-2 text-sm text-muted-foreground">
              <Info className="mt-0.5 size-4 shrink-0" />
              Lo que otros sistemas dejaron para facturar acá. Elegí uno o varios
              del <strong>mismo cliente</strong> para juntarlos en una factura —
              nada se emite hasta que lo confirmes en el formulario.
            </p>
          )}

          {loading
            ? <p className="text-sm text-muted-foreground">Cargando…</p>
            : filas.length === 0
              ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  {tab === 'pendientes' ? 'No hay nada esperando para facturar.' : 'Todavía no hay nada acá.'}
                </p>
              )
              : (
                <DataTable
                  columns={tab === 'pendientes' ? columnsPendientes : columnsResueltos}
                  data={filas}
                />
              )}

          {tab === 'pendientes' && elegidos.length > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-muted/40 p-3">
              {/* La frase entera en un solo nodo: partida en `<strong>{n}</strong>`
                  más texto suelto, quedaba imposible de buscar por texto y —lo
                  que importa más— la lee mal un lector de pantalla. */}
              <p className="text-sm">
                <strong>
                  {elegidos.length === 1
                    ? '1 comprobante elegido'
                    : `${elegidos.length} comprobantes elegidos`}
                </strong>
                {' · '}
                <strong>{formatCurrency(totalElegido)}</strong>
              </p>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setElegidos([])}>Limpiar</Button>
                <Button disabled={saving} onClick={facturar}>
                  <ReceiptText className="mr-1 size-4" />
                  {saving ? 'Preparando…' : 'Facturar'}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {descartando && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Descartar comprobante</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <p className="text-sm text-muted-foreground">
              {descartando.cliente_razon} · {formatCurrency(descartando.total)}.
              No se factura y el sistema de origen deja de reenviarlo.
            </p>
            <div className="grid gap-1.5">
              <Label htmlFor="motivo">Motivo</Label>
              <Input
                id="motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)}
                placeholder="Ej: se cobró por fuera"
              />
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setDescartando(null)}>Cancelar</Button>
              <Button variant="destructive" disabled={saving} onClick={confirmarDescarte}>
                Descartar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
