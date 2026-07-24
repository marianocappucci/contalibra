import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError, type AliasFacturacion, type ClienteConAlias } from '../api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { IdCard, Pencil, Undo2, ArrowLeft, ArrowLeftRight, Plus, Trash2 } from 'lucide-react'

// Restaurado desde web/templates/clientes/detail.html: auto-factura MP
// (toggle) y alias de facturacion (CUIT/email -> este cliente) ya tienen
// endpoint real en web/api/clientes.py (GET/{id}, toggle-auto-facturar,
// alias-facturacion) -- ver wiki/entities/contalibra.md.
export function ClienteDetalle() {
  const { id } = useParams<{ id: string }>()
  const clienteId = Number(id)
  const navigate = useNavigate()

  const [cliente, setCliente] = useState<ClienteConAlias | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toggling, setToggling] = useState(false)
  const [aliasTipo, setAliasTipo] = useState<'cuit' | 'email'>('cuit')
  const [aliasValor, setAliasValor] = useState('')
  const [aliasError, setAliasError] = useState<string | null>(null)
  const [savingAlias, setSavingAlias] = useState(false)

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteId])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function cargar() {
    setLoading(true)
    setError(null)
    try {
      setCliente(await api.get<ClienteConAlias>(`/api/clientes/${clienteId}`))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function reactivar() {
    if (!cliente) return
    setError(null)
    try {
      await api.post(`/api/clientes/${cliente.id}/activar`)
      await cargar()
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function toggleAutoFacturar() {
    if (!cliente) return
    setToggling(true)
    setError(null)
    try {
      await api.post(`/api/clientes/${cliente.id}/toggle-auto-facturar`)
      await cargar()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setToggling(false)
    }
  }

  async function agregarAlias() {
    if (!cliente || !aliasValor.trim()) return
    setSavingAlias(true)
    setAliasError(null)
    try {
      const alias = await api.post<AliasFacturacion[]>(`/api/clientes/${cliente.id}/alias-facturacion`, {
        tipo: aliasTipo, valor: aliasValor,
      })
      setCliente({ ...cliente, alias_facturacion: alias })
      setAliasValor('')
    } catch (err) {
      setAliasError(describeError(err))
    } finally {
      setSavingAlias(false)
    }
  }

  async function eliminarAlias(aliasId: number) {
    if (!cliente) return
    if (!window.confirm('¿Quitar este alias de facturación?')) return
    setAliasError(null)
    try {
      const alias = await api.del<AliasFacturacion[]>(`/api/clientes/${cliente.id}/alias-facturacion/${aliasId}`)
      setCliente({ ...cliente, alias_facturacion: alias })
    } catch (err) {
      setAliasError(describeError(err))
    }
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <IdCard className="size-5 text-primary" />
            {cliente ? cliente.name : 'Cliente'}
          </h2>
          {cliente && !cliente.activo && <Badge variant="secondary">Inactivo</Badge>}
        </div>
        <div className="flex flex-wrap gap-2">
          {cliente && cliente.activo && (
            <Button asChild size="sm" variant="outline"><Link to={`/clientes/${cliente.id}/editar`}><Pencil />Editar</Link></Button>
          )}
          {cliente && !cliente.activo && (
            <Button size="sm" variant="outline" onClick={reactivar}><Undo2 />Reactivar cliente</Button>
          )}
          <Button asChild size="sm" variant="outline"><Link to="/clientes"><ArrowLeft />Volver</Link></Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading ? (
        <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
      ) : cliente && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Datos del cliente</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-1.5 text-sm">
              <p><span className="text-muted-foreground">Nombre / Razón social:</span> <span className="font-medium">{cliente.name}</span></p>
              {cliente.cuit_dni && <p><span className="text-muted-foreground">CUIT / DNI:</span> <span className="font-mono">{cliente.cuit_dni}</span></p>}
              {cliente.iva_condition && <p><span className="text-muted-foreground">Condición IVA:</span> {cliente.iva_condition}</p>}
              {cliente.address && <p><span className="text-muted-foreground">Domicilio:</span> {cliente.address}</p>}
              {cliente.phone && <p><span className="text-muted-foreground">Teléfono:</span> {cliente.phone}</p>}
              {cliente.email && <p><span className="text-muted-foreground">Email:</span> <a className="underline" href={`mailto:${cliente.email}`}>{cliente.email}</a></p>}
              <div className="flex items-center gap-2 pt-1">
                <span className="text-muted-foreground">Auto-factura MP:</span>
                <Switch checked={Boolean(cliente.auto_facturar)} disabled={toggling} onCheckedChange={toggleAutoFacturar} />
                <span className="text-xs text-muted-foreground">{cliente.auto_facturar ? 'Activa' : 'Inactiva'}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><ArrowLeftRight className="size-4" />Alias de facturación (Mercado Pago)</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3">
              <p className="text-xs text-muted-foreground">
                Si un pago de MP llega con un CUIT o email distinto al de este cliente (por ejemplo, paga con otra
                cuenta), agregá ese CUIT o email acá para que se facture igual a <strong>{cliente.name}</strong> en
                vez de crear un cliente nuevo.
              </p>

              {aliasError && <p className="text-sm text-destructive">{aliasError}</p>}

              {cliente.alias_facturacion.length > 0 ? (
                <ul className="divide-y">
                  {cliente.alias_facturacion.map((a) => (
                    <li key={a.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                      <span className="flex items-center gap-2">
                        <Badge variant="secondary">{a.tipo === 'cuit' ? 'CUIT' : 'Email'}</Badge>
                        <span className="font-mono">{a.valor}</span>
                      </span>
                      <Button size="icon" variant="outline" onClick={() => eliminarAlias(a.id)}><Trash2 /></Button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">Todavía no hay alias configurados para este cliente.</p>
              )}

              <div className="flex flex-wrap items-end gap-2 border-t pt-3">
                <div className="grid gap-1.5">
                  <Label>Tipo</Label>
                  <Select value={aliasTipo} onValueChange={(v) => setAliasTipo(v as 'cuit' | 'email')}>
                    <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cuit">CUIT</SelectItem>
                      <SelectItem value="email">Email</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-1.5">
                  <Label>Valor</Label>
                  <Input value={aliasValor} onChange={(e) => setAliasValor(e.target.value)} placeholder="20-12345678-9 o correo@ejemplo.com" className="w-56" />
                </div>
                <Button size="sm" variant="outline" disabled={savingAlias || !aliasValor.trim()} onClick={agregarAlias}>
                  <Plus />{savingAlias ? 'Agregando…' : 'Agregar alias'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {!loading && !cliente && !error && (
        <p className="py-6 text-center text-sm text-muted-foreground">Cliente no encontrado.</p>
      )}
      {!loading && error === 'Cliente no encontrado' && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => navigate('/clientes')}>Volver al listado</Button>
        </div>
      )}
    </div>
  )
}
