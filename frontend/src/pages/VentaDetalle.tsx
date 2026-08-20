import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, ApiError, MEDIOS_PAGO_LABELS, type Venta } from '../api'
import { useAuth } from '../context/AuthContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ConfirmDialog } from '@/components/confirm-dialog'
import {
  ArrowLeft, Printer, FileCheck, CheckCircle2, Ban, ReceiptText, PackageCheck, QrCode, Loader2,
} from 'lucide-react'

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value)
}

const estadoVariant: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  cobrada: 'default', parcial: 'secondary', pendiente: 'outline', anulada: 'destructive',
}

const ESTADO_LABELS: Record<string, string> = {
  cobrada: 'Cobrada', parcial: 'Pago parcial', pendiente: 'Pendiente', anulada: 'Anulada',
}
function estadoLabel(estado: string): string {
  return ESTADO_LABELS[estado] ?? estado
}

type QrEstado = 'idle' | 'creando' | 'esperando' | 'acreditado'

/** Dos notas cortas, sintetizadas. Sin archivo de audio a propósito: no hay
 *  nada que descargar ni que sirva el backend, y suena igual sin internet.
 *
 *  El `AudioContext` se crea con el click de "Cobrar con QR" y no al acreditar:
 *  los navegadores bloquean el audio que no nace de un gesto del usuario, y la
 *  acreditación llega desde un `setInterval`, que no cuenta como gesto. */
function crearAudio(): AudioContext | null {
  try {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    return Ctor ? new Ctor() : null
  } catch {
    return null
  }
}

function sonarCampanita(ctx: AudioContext | null) {
  if (!ctx) return
  // Un contexto creado antes de cualquier gesto puede quedar suspendido.
  if (ctx.state === 'suspended') void ctx.resume()
  const notas = [
    { hz: 1318.5, en: 0 },      // mi6
    { hz: 1760.0, en: 0.13 },   // la6
  ]
  for (const { hz, en } of notas) {
    const osc = ctx.createOscillator()
    const vol = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.value = hz
    const t = ctx.currentTime + en
    vol.gain.setValueAtTime(0.0001, t)
    vol.gain.exponentialRampToValueAtTime(0.28, t + 0.01)
    vol.gain.exponentialRampToValueAtTime(0.0001, t + 0.42)
    osc.connect(vol).connect(ctx.destination)
    osc.start(t)
    osc.stop(t + 0.45)
  }
}

const POLL_MS = 3000
// Cinco minutos: pasado eso el cliente ya se fue del mostrador. Cortar el poll
// no cancela nada del lado de MercadoPago — si paga después, el webhook lo
// acredita igual.
const ESPERA_MAXIMA_MS = 5 * 60 * 1000

//: Los medios que se cobran escaneando el QR de la caja. `add_venta_pago_referencia_mp`
//  (db_ventas.py) sella la referencia sobre una fila de pago con uno de estos
//  medios: sin esa fila el pago se acredita en MercadoPago y no queda atado a
//  la venta.
const MEDIOS_QR = ['mercadopago', 'billetera', 'cuenta_dni', 'qr']

export function VentaDetalle() {
  const { id } = useParams<{ id: string }>()
  const ventaId = Number(id)
  const { user } = useAuth()

  const [detalle, setDetalle] = useState<Venta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [confirmAnular, setConfirmAnular] = useState(false)
  const [facturando, setFacturando] = useState(false)
  const [qrEstado, setQrEstado] = useState<QrEstado>('idle')
  const [qrError, setQrError] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)
  const audioRef = useRef<AudioContext | null>(null)

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ventaId])

  // Sin esto el poll sigue corriendo contra una venta que ya no está en
  // pantalla: el usuario navega a otra y cada 3 segundos sale un request.
  useEffect(() => frenarPoll, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function cargar() {
    setLoading(true)
    setError(null)
    try {
      setDetalle(await api.get<Venta>(`/api/ventas/${ventaId}`))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function anular() {
    if (!detalle) return
    setError(null)
    try {
      await api.post(`/api/ventas/${detalle.id}/anular`)
      await cargar()
    } catch (err) {
      setError(describeError(err))
    }
  }

  function frenarPoll() {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  // Empuja el monto de la venta al punto de venta de MercadoPago. El QR es el
  // fijo de la caja —el cartel impreso—, así que no hay nada que mostrar en
  // pantalla: lo que cambia es qué cobra ese QR cuando alguien lo escanea.
  async function cobrarConQr() {
    if (!detalle) return
    // Acá, con el click todavía en curso, es el único momento en que el
    // navegador deja abrir el audio.
    audioRef.current = audioRef.current ?? crearAudio()
    setQrError(null)
    setQrEstado('creando')
    try {
      await api.post(`/ventas/${detalle.id}/mp-qr`)
    } catch (err) {
      setQrError(describeError(err))
      setQrEstado('idle')
      return
    }
    setQrEstado('esperando')
    const hasta = Date.now() + ESPERA_MAXIMA_MS
    pollRef.current = window.setInterval(async () => {
      let estado: string
      try {
        estado = (await api.get<{ status: string }>(`/ventas/${detalle.id}/mp-status`)).status
      } catch (err) {
        frenarPoll()
        setQrEstado('idle')
        setQrError(describeError(err))
        return
      }
      if (estado === 'approved') {
        frenarPoll()
        sonarCampanita(audioRef.current)
        setQrEstado('acreditado')
        await cargar()
        return
      }
      if (estado === 'rejected' || estado === 'cancelled') {
        frenarPoll()
        setQrEstado('idle')
        setQrError('El pago fue rechazado o cancelado en MercadoPago.')
        return
      }
      if (Date.now() > hasta) {
        frenarPoll()
        setQrEstado('idle')
        setQrError('Se agotó la espera. Si el cliente pagó igual, el cobro se acredita solo cuando MercadoPago avise; si no, volvé a intentar.')
      }
    }, POLL_MS)
  }

  async function facturar() {
    if (!detalle) return
    setError(null)
    setFacturando(true)
    try {
      await api.post(`/api/ventas/${detalle.id}/facturar`)
      await cargar()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setFacturando(false)
    }
  }

  // Sin una fila de pago con medio de QR no hay dónde sellar la referencia del
  // cobro, así que el botón no se ofrece: ver el comentario de MEDIOS_QR.
  const puedeCobrarConQr = !!detalle
    && detalle.estado !== 'anulada'
    && !detalle.mp_payment_id
    && detalle.pagos.some((p) => MEDIOS_QR.includes(p.medio))

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <ReceiptText className="size-5 text-primary" />
          {detalle ? <>Venta {detalle.numero} <Badge variant={estadoVariant[detalle.estado] ?? 'outline'}>{estadoLabel(detalle.estado)}</Badge></> : 'Venta'}
        </h2>
        {detalle && (
          <div className="flex flex-wrap gap-2">
            <Button asChild size="sm" variant="outline"><a href={`/ventas/${detalle.id}/ticket`} target="_blank" rel="noreferrer"><Printer />Ticket</a></Button>
            {detalle.pagos.length > 0 && (
              <Button asChild size="sm" variant="outline"><a href={`/ventas/${detalle.id}/recibo`} target="_blank" rel="noreferrer"><FileCheck />Recibo</a></Button>
            )}
            <Button asChild size="sm" variant="outline"><Link to="/ventas"><ArrowLeft />Volver</Link></Button>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading || !detalle ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-base">Datos de la venta</CardTitle></CardHeader>
              <CardContent className="grid gap-1.5 text-sm">
                <p><span className="text-muted-foreground">Fecha:</span> {detalle.fecha}</p>
                <p><span className="text-muted-foreground">Cliente:</span> {detalle.cliente_nombre || '— Consumidor final —'}</p>
                {detalle.observaciones && <p><span className="text-muted-foreground">Obs.:</span> {detalle.observaciones}</p>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2 text-base"><CheckCircle2 className="size-4" />Pagos recibidos</CardTitle></CardHeader>
              <CardContent className="grid gap-1.5 text-sm">
                {detalle.pagos.length === 0 ? (
                  <p className="text-muted-foreground">Sin pagos registrados.</p>
                ) : (
                  <>
                    {detalle.pagos.map((p, i) => (
                      <div key={i} className="grid gap-0.5">
                        <div className="flex justify-between">
                          <Badge variant="outline">{MEDIOS_PAGO_LABELS[p.medio] ?? p.medio}</Badge>
                          <span className="font-medium">{formatCurrency(p.monto)}</span>
                        </div>
                        {p.referencia && <p className="flex items-center gap-1 text-xs text-muted-foreground"><CheckCircle2 className="size-3.5 text-emerald-600" />Ref: {p.referencia}</p>}
                      </div>
                    ))}
                    <div className="mt-1 flex justify-between border-t pt-1.5 font-semibold">
                      <span>Total cobrado</span><span>{formatCurrency(detalle.pagos.reduce((a, p) => a + p.monto, 0))}</span>
                    </div>
                    {detalle.mp_payment_id ? (
                      <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground"><QrCode className="size-3.5" />Cobrado por QR de MercadoPago.</p>
                    ) : puedeCobrarConQr && (
                      <div className="mt-2 grid gap-2 border-t pt-2">
                        {qrEstado === 'esperando' ? (
                          <>
                            <p className="flex items-center gap-1.5 text-xs font-medium text-amber-700 dark:text-amber-400">
                              <Loader2 className="size-3.5 animate-spin" />Esperando el pago…
                            </p>
                            <p className="text-xs text-muted-foreground">
                              El QR de la caja ya está cobrando {formatCurrency(detalle.total)}. Pedile al cliente que lo escanee.
                            </p>
                          </>
                        ) : qrEstado === 'acreditado' ? (
                          <p className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                            <CheckCircle2 className="size-3.5" />Pago acreditado.
                          </p>
                        ) : (
                          <Button size="sm" variant="outline" disabled={qrEstado === 'creando'} onClick={cobrarConQr}>
                            <QrCode />{qrEstado === 'creando' ? 'Preparando el QR…' : 'Cobrar con QR'}
                          </Button>
                        )}
                        {qrError && <p className="text-xs text-destructive">{qrError}</p>}
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </div>

          {(detalle.factura_display || detalle.remito_id) && (
            <div className="grid gap-2 sm:grid-cols-2">
              {detalle.factura_display && (
                <p className="flex items-center gap-2 rounded-md border bg-muted/50 p-3 text-sm"><ReceiptText className="size-4 text-emerald-600" />Factura generada: <Link to={`/facturas/${detalle.factura_id}`} className="font-semibold text-emerald-600 hover:underline dark:text-emerald-400">ver factura</Link></p>
              )}
              {detalle.remito_id && (
                <p className="flex items-center gap-2 rounded-md border bg-muted/50 p-3 text-sm"><PackageCheck className="size-4 text-primary" />Remito generado: <Link to={`/remitos/${detalle.remito_id}`} className="font-semibold text-primary hover:underline">ver remito</Link></p>
              )}
            </div>
          )}

          <Card>
            <CardHeader><CardTitle className="text-base">Artículos vendidos</CardTitle></CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead className="border-b text-muted-foreground">
                  <tr>
                    <th className="p-3 text-left font-medium">Descripción</th>
                    <th className="p-3 text-right font-medium">Cant.</th>
                    <th className="p-3 text-right font-medium">Precio unit.</th>
                    <th className="p-3 text-right font-medium">Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  {detalle.items.map((it, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="p-3">{it.nombre}</td>
                      <td className="p-3 text-right">{it.qty}</td>
                      <td className="p-3 text-right">{formatCurrency(it.precio)}</td>
                      <td className="p-3 text-right font-medium">{formatCurrency(it.subtotal)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="font-medium">
                  <tr><td colSpan={3} className="p-3 text-right text-muted-foreground">Subtotal</td><td className="p-3 text-right">{formatCurrency(detalle.subtotal)}</td></tr>
                  {detalle.descuento > 0 && (
                    <tr><td colSpan={3} className="p-3 text-right text-muted-foreground">Descuento</td><td className="p-3 text-right text-destructive">− {formatCurrency(detalle.descuento)}</td></tr>
                  )}
                  <tr className="text-base"><td colSpan={3} className="p-3 text-right font-semibold">TOTAL</td><td className="p-3 text-right font-semibold text-primary">{formatCurrency(detalle.total)}</td></tr>
                </tfoot>
              </table>
            </CardContent>
          </Card>

          {(detalle.estado === 'cobrada' || detalle.estado === 'parcial') && (
            <div className="flex flex-wrap justify-end gap-2 border-t pt-4">
              {!detalle.factura_id && (
                <Button size="sm" variant="outline" disabled={facturando} onClick={facturar}>
                  <ReceiptText />{facturando ? 'Facturando…' : 'Generar factura'}
                </Button>
              )}
              {!detalle.remito_id && <Button asChild size="sm" variant="outline"><Link to="/remitos/nuevo"><PackageCheck />Generar remito</Link></Button>}
              {user?.role === 'admin' && (
                <Button size="sm" variant="outline" className="text-destructive hover:text-destructive" onClick={() => setConfirmAnular(true)}><Ban />Anular venta</Button>
              )}
            </div>
          )}
        </>
      )}

      <ConfirmDialog
        open={confirmAnular}
        onOpenChange={setConfirmAnular}
        title="¿Anular esta venta?"
        description="Se repondrá el stock, se revertirán los movimientos de caja y, si tenía pago a cuenta corriente, se acreditará la deuda del cliente."
        confirmLabel="Anular"
        onConfirm={() => { anular(); setConfirmAnular(false) }}
      />
    </div>
  )
}
