import { useEffect, useState, type ChangeEvent } from 'react'
import { api, ApiError, type ArcaConfig, type Backup, type CategoriaEgreso, type ConfigCfg } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Ban, Building2, Check, CheckCircle2, Copy, CreditCard, Database, Download,
  Mail, Package, Pause, Plus, Power, Printer, Receipt, Save, Send, Settings,
  ShieldCheck, Tag, Trash2, Upload,
} from 'lucide-react'

type CategoriaProducto = { id: number; nombre: string }

const TABS = [
  { id: 'empresa', label: 'Empresa', icon: Building2 },
  { id: 'mp', label: 'MercadoPago', icon: CreditCard },
  { id: 'email', label: 'Email', icon: Mail },
  { id: 'arca', label: 'ARCA', icon: ShieldCheck },
  { id: 'servicio', label: 'Servicio', icon: Power },
  { id: 'ticket', label: 'Ticket', icon: Printer },
  { id: 'categorias', label: 'Categorías', icon: Tag },
  { id: 'datos', label: 'Datos', icon: Database },
] as const
type TabId = typeof TABS[number]['id']

export function Config() {
  const [tab, setTab] = useState<TabId>('empresa')
  const [cfg, setCfg] = useState<ConfigCfg | null>(null)
  const [arca, setArca] = useState<ArcaConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    load()
  }, [])

  function describeError(err: unknown): string {
    if (err instanceof ApiError) return err.detail
    return 'Error de conexión.'
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<{ cfg: ConfigCfg; arca: ArcaConfig }>('/api/config')
      setCfg(data.cfg)
      setArca(data.arca)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  async function guardar<T>(path: string, payload: T, onDone?: () => void) {
    setSaving(true)
    setError(null)
    setSaved(null)
    try {
      await api.put(path, payload)
      setSaved(tab)
      onDone?.()
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  async function subirArchivo(path: string, field: string, file: File) {
    setSaving(true)
    setError(null)
    try {
      const form = new FormData()
      form.append(field, file)
      await api.postForm(path, form)
      await load()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
    }
  }

  if (loading || !cfg) {
    return <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
  }

  return (
    <div className="grid gap-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold"><Settings className="size-5" />Configuración</h2>

      <div className="flex flex-wrap gap-1 border-b pb-2">
        {TABS.map((t) => (
          <Button
            key={t.id} size="sm" variant={tab === t.id ? 'default' : 'ghost'}
            onClick={() => { setTab(t.id); setSaved(null); setError(null) }}
          >
            <t.icon />{t.label}
          </Button>
        ))}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {saved === tab && <p className="text-sm text-emerald-600 dark:text-emerald-400">Guardado.</p>}

      {tab === 'empresa' && <EmpresaTab cfg={cfg} setCfg={setCfg} saving={saving} guardar={guardar} subirArchivo={subirArchivo} />}
      {tab === 'mp' && <MpTab cfg={cfg} setCfg={setCfg} saving={saving} guardar={guardar} />}
      {tab === 'email' && <EmailTab cfg={cfg} setCfg={setCfg} saving={saving} guardar={guardar} />}
      {tab === 'arca' && <ArcaTab arca={arca} setArca={setArca} saving={saving} guardar={guardar} subirArchivo={subirArchivo} />}
      {tab === 'servicio' && <ServicioTab cfg={cfg} setCfg={setCfg} saving={saving} guardar={guardar} />}
      {tab === 'ticket' && <TicketTab cfg={cfg} setCfg={setCfg} saving={saving} guardar={guardar} />}
      {tab === 'categorias' && <CategoriasTab />}
      {tab === 'datos' && <DatosTab saving={saving} setSaving={setSaving} setError={setError} describeError={describeError} />}
    </div>
  )
}

type GuardarFn = <T>(path: string, payload: T, onDone?: () => void) => Promise<void>

function EmpresaTab({ cfg, setCfg, saving, guardar, subirArchivo }: {
  cfg: ConfigCfg; setCfg: (c: ConfigCfg) => void; saving: boolean
  guardar: GuardarFn; subirArchivo: (path: string, field: string, file: File) => Promise<void>
}) {
  function handleLogo(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) subirArchivo('/api/config/empresa/logo', 'logo', file)
  }

  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Building2 className="size-4" />Datos de la empresa</CardTitle></CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <Field label="Nombre" value={cfg.empresa_nombre} onChange={(v) => setCfg({ ...cfg, empresa_nombre: v })} />
        <Field label="CUIT" value={cfg.empresa_cuit} onChange={(v) => setCfg({ ...cfg, empresa_cuit: v })} />
        <Field label="Dirección" value={cfg.empresa_direccion} onChange={(v) => setCfg({ ...cfg, empresa_direccion: v })} />
        <Field label="Teléfono" value={cfg.empresa_telefono} onChange={(v) => setCfg({ ...cfg, empresa_telefono: v })} />
        <Field label="Email" value={cfg.empresa_email} onChange={(v) => setCfg({ ...cfg, empresa_email: v })} />
        <Field label="Ingresos Brutos" value={cfg.empresa_iibb} onChange={(v) => setCfg({ ...cfg, empresa_iibb: v })} />
        <div className="grid gap-1.5">
          <Label>Condición de IVA</Label>
          <Select value={cfg.empresa_iva_condition} onValueChange={(v) => setCfg({ ...cfg, empresa_iva_condition: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="Monotributista">Monotributista (emite Factura C)</SelectItem>
              <SelectItem value="Responsable Inscripto">Responsable Inscripto (emite Factura A y B)</SelectItem>
              <SelectItem value="IVA Exento">IVA Exento (emite Factura B)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Field label="Inicio de actividades" type="date" value={cfg.empresa_inicio_actividades} onChange={(v) => setCfg({ ...cfg, empresa_inicio_actividades: v })} />
        <div className="col-span-full grid gap-1.5">
          <Label>Logo (PNG o JPG)</Label>
          {cfg.logo_path && (
            <div className="flex items-center gap-3">
              <img src="/config/empresa/logo" alt="Logo actual" className="h-16 max-w-48 rounded-md border bg-white object-contain p-1.5" />
              <Badge className="bg-emerald-600 text-white hover:bg-emerald-600/90 dark:bg-emerald-500"><CheckCircle2 />Logo cargado</Badge>
            </div>
          )}
          <Input type="file" accept=".png,.jpg,.jpeg" onChange={handleLogo} disabled={saving} className="max-w-sm" />
          <p className="text-xs text-muted-foreground">PNG o JPG. Dejalo vacío para mantener el logo actual.</p>
        </div>
        <div className="col-span-full">
          <Button disabled={saving} onClick={() => guardar('/api/config/empresa', {
            empresa_nombre: cfg.empresa_nombre, empresa_direccion: cfg.empresa_direccion,
            empresa_cuit: cfg.empresa_cuit, empresa_telefono: cfg.empresa_telefono,
            empresa_email: cfg.empresa_email, empresa_iibb: cfg.empresa_iibb,
            empresa_iva_condition: cfg.empresa_iva_condition,
            empresa_inicio_actividades: cfg.empresa_inicio_actividades,
          })}>
            <Save />{saving ? 'Guardando…' : 'Guardar datos de empresa'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function MpTab({ cfg, setCfg, saving, guardar }: {
  cfg: ConfigCfg; setCfg: (c: ConfigCfg) => void; saving: boolean; guardar: GuardarFn
}) {
  const [probando, setProbando] = useState(false)
  const [resultado, setResultado] = useState<string | null>(null)
  const [copiado, setCopiado] = useState(false)
  const webhookUrl = `${window.location.origin}/webhooks/mercadopago`

  async function probar() {
    setProbando(true)
    setResultado(null)
    try {
      const r = await api.get<{ ok: boolean; nickname?: string; error?: string }>('/api/mp/probar')
      setResultado(r.ok ? `Conectado — ${r.nickname}` : r.error ?? 'Error')
    } catch (err) {
      setResultado(err instanceof ApiError ? err.detail : 'Error de conexión.')
    } finally {
      setProbando(false)
    }
  }

  function copiarWebhook() {
    navigator.clipboard.writeText(webhookUrl).then(() => {
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2000)
    })
  }

  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2 text-base"><CreditCard className="size-4" />MercadoPago</CardTitle></CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <Field label="Access Token" type="password" value={cfg.mp_access_token} onChange={(v) => setCfg({ ...cfg, mp_access_token: v })} />
        <Field label="Webhook Secret" type="password" value={cfg.mp_webhook_secret} onChange={(v) => setCfg({ ...cfg, mp_webhook_secret: v })} />
        <Field label="Descripción del cobro" value={cfg.mp_concepto_descripcion} onChange={(v) => setCfg({ ...cfg, mp_concepto_descripcion: v })} />
        <div className="grid gap-1.5">
          <Label>Alícuota IVA</Label>
          <Select value={cfg.mp_iva_rate || '0'} onValueChange={(v) => setCfg({ ...cfg, mp_iva_rate: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="0">Sin IVA (Monotributista / Exento)</SelectItem>
              <SelectItem value="0.21">21%</SelectItem>
              <SelectItem value="0.105">10,5%</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Field label="User ID (QR)" value={cfg.mp_user_id} onChange={(v) => setCfg({ ...cfg, mp_user_id: v })} />
        <Field label="POS ID (QR)" value={cfg.mp_pos_id} onChange={(v) => setCfg({ ...cfg, mp_pos_id: v })} />
        <div className="col-span-full grid gap-1.5 rounded-md border bg-muted/40 p-3 text-sm">
          <p className="font-medium">URL del webhook para registrar en MercadoPago</p>
          <div className="flex gap-2">
            <Input readOnly value={webhookUrl} className="font-mono text-xs" />
            <Button type="button" size="sm" variant="outline" onClick={copiarWebhook}>
              {copiado ? <Check /> : <Copy />}{copiado ? 'Copiado' : 'Copiar'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">Evento a suscribir: Pagos (payment). El Webhook Secret lo genera MP al guardar el webhook.</p>
        </div>
        <div className="col-span-full flex items-center gap-3">
          <Button disabled={saving} onClick={() => guardar('/api/config/mp', {
            mp_access_token: cfg.mp_access_token, mp_webhook_secret: cfg.mp_webhook_secret,
            mp_concepto_descripcion: cfg.mp_concepto_descripcion, mp_iva_rate: cfg.mp_iva_rate,
            mp_user_id: cfg.mp_user_id, mp_pos_id: cfg.mp_pos_id,
          })}>
            <Save />{saving ? 'Guardando…' : 'Guardar MercadoPago'}
          </Button>
          {cfg.mp_access_token && (
            <Button type="button" variant="outline" disabled={probando} onClick={probar}>
              <Send />{probando ? 'Probando…' : 'Probar conexión'}
            </Button>
          )}
          {resultado && <span className="text-sm text-muted-foreground">{resultado}</span>}
        </div>
      </CardContent>
    </Card>
  )
}

function EmailTab({ cfg, setCfg, saving, guardar }: {
  cfg: ConfigCfg; setCfg: (c: ConfigCfg) => void; saving: boolean; guardar: GuardarFn
}) {
  const [probando, setProbando] = useState(false)
  const [resultado, setResultado] = useState<string | null>(null)

  async function probar() {
    setProbando(true)
    setResultado(null)
    try {
      const r = await api.get<{ ok: boolean; host?: string; error?: string }>('/api/email/probar')
      setResultado(r.ok ? `Conectado — ${r.host}` : r.error ?? 'Error')
    } catch (err) {
      setResultado(err instanceof ApiError ? err.detail : 'Error de conexión.')
    } finally {
      setProbando(false)
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Mail className="size-4" />Email (SMTP)</CardTitle></CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <Field label="Host SMTP" value={cfg.email_smtp_host} onChange={(v) => setCfg({ ...cfg, email_smtp_host: v })} />
        <Field label="Puerto" value={cfg.email_smtp_port} onChange={(v) => setCfg({ ...cfg, email_smtp_port: v })} />
        <Field label="Usuario" value={cfg.email_smtp_user} onChange={(v) => setCfg({ ...cfg, email_smtp_user: v })} />
        <Field label="Contraseña (dejar vacío para no cambiar)" type="password" value={cfg.email_smtp_password} onChange={(v) => setCfg({ ...cfg, email_smtp_password: v })} />
        <Field label="Remitente" value={cfg.email_from} onChange={(v) => setCfg({ ...cfg, email_from: v })} />
        <Field label="Nombre del remitente" value={cfg.email_from_name} onChange={(v) => setCfg({ ...cfg, email_from_name: v })} />
        <div className="col-span-full flex items-center gap-3">
          <Button disabled={saving} onClick={() => guardar('/api/config/email', {
            email_smtp_host: cfg.email_smtp_host, email_smtp_port: cfg.email_smtp_port,
            email_smtp_user: cfg.email_smtp_user, email_smtp_password: cfg.email_smtp_password,
            email_from: cfg.email_from, email_from_name: cfg.email_from_name,
          })}>
            <Save />{saving ? 'Guardando…' : 'Guardar email'}
          </Button>
          {cfg.email_smtp_host && cfg.email_smtp_user && cfg.email_smtp_password && (
            <Button type="button" variant="outline" disabled={probando} onClick={probar}>
              <Send />{probando ? 'Probando…' : 'Probar conexión'}
            </Button>
          )}
          {resultado && <span className="text-sm text-muted-foreground">{resultado}</span>}
        </div>
      </CardContent>
    </Card>
  )
}

function ArcaTab({ arca, setArca, saving, guardar, subirArchivo }: {
  arca: ArcaConfig | null; setArca: (a: ArcaConfig) => void; saving: boolean
  guardar: GuardarFn; subirArchivo: (path: string, field: string, file: File) => Promise<void>
}) {
  const [probando, setProbando] = useState(false)
  const [resultado, setResultado] = useState<string | null>(null)
  const a: ArcaConfig = arca ?? { empresa: 'default', cuit: '', punto_venta: 1, ambiente: 'homologacion', alias: '', clave_path: '', certificado_path: '' }

  async function probar() {
    setProbando(true)
    setResultado(null)
    try {
      const r = await api.get<{ ok: boolean; ambiente?: string; error?: string }>('/api/arca/probar')
      setResultado(r.ok ? `Autenticado OK (${r.ambiente})` : r.error ?? 'Error')
    } catch (err) {
      setResultado(err instanceof ApiError ? err.detail : 'Error de conexión.')
    } finally {
      setProbando(false)
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle className="flex items-center gap-2 text-base"><ShieldCheck className="size-4" />ARCA (facturación electrónica)</CardTitle></CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <Field label="CUIT" value={a.cuit} onChange={(v) => setArca({ ...a, cuit: v })} />
        <Field label="Punto de venta" value={String(a.punto_venta)} onChange={(v) => setArca({ ...a, punto_venta: Number(v) || 1 })} />
        <div className="grid gap-1.5">
          <Label>Ambiente</Label>
          <Select value={a.ambiente} onValueChange={(v) => setArca({ ...a, ambiente: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="homologacion">Homologación (pruebas)</SelectItem>
              <SelectItem value="produccion">Producción</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Field label="Alias" value={a.alias} onChange={(v) => setArca({ ...a, alias: v })} />
        <div className="grid gap-1.5">
          <Label>Certificado (.crt)</Label>
          {a.certificado_path && (
            <Badge className="w-fit bg-emerald-600 text-white hover:bg-emerald-600/90 dark:bg-emerald-500"><CheckCircle2 />Cargado</Badge>
          )}
          <Input type="file" accept=".crt,.pem" disabled={saving}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) subirArchivo(`/api/config/arca/certificados?empresa=${a.empresa}`, 'certificado', f) }} />
          {a.certificado_path && <p className="truncate text-xs text-muted-foreground">Actual: {a.certificado_path}</p>}
        </div>
        <div className="grid gap-1.5">
          <Label>Clave privada (.key)</Label>
          {a.clave_path && (
            <Badge className="w-fit bg-emerald-600 text-white hover:bg-emerald-600/90 dark:bg-emerald-500"><CheckCircle2 />Cargada</Badge>
          )}
          <Input type="file" accept=".key,.pem" disabled={saving}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) subirArchivo(`/api/config/arca/certificados?empresa=${a.empresa}`, 'clave_privada', f) }} />
          {a.clave_path && <p className="truncate text-xs text-muted-foreground">Actual: {a.clave_path}</p>}
        </div>
        <div className="col-span-full flex items-center gap-3">
          <Button disabled={saving} onClick={() => guardar('/api/config/arca', {
            empresa: a.empresa, cuit: a.cuit, punto_venta: a.punto_venta, ambiente: a.ambiente, alias: a.alias,
          })}>
            <Save />{saving ? 'Guardando…' : 'Guardar ARCA'}
          </Button>
          {a.certificado_path && a.clave_path && (
            <Button type="button" variant="outline" disabled={probando} onClick={probar}>
              <Send />{probando ? 'Probando…' : 'Probar conexión'}
            </Button>
          )}
          {resultado && <span className="text-sm text-muted-foreground">{resultado}</span>}
        </div>
      </CardContent>
    </Card>
  )
}

function ServicioTab({ cfg, setCfg, saving, guardar }: {
  cfg: ConfigCfg; setCfg: (c: ConfigCfg) => void; saving: boolean; guardar: GuardarFn
}) {
  const estadoInfo: Record<ConfigCfg['servicio_estado'], { icon: typeof CheckCircle2; color: string; desc: string }> = {
    activo: { icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400', desc: 'Operación normal. Todos los usuarios tienen acceso completo.' },
    pausado: { icon: Pause, color: 'text-amber-600 dark:text-amber-400', desc: 'Los usuarios pueden ingresar pero ven un banner de aviso.' },
    suspendido: { icon: Ban, color: 'text-destructive', desc: 'Acceso bloqueado por completo. Se muestra la página de suspensión.' },
  }
  const Icon = estadoInfo[cfg.servicio_estado].icon

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base"><Power className="size-4" />Estado del servicio</CardTitle>
        <CardDescription>Suspender bloquea el acceso de los usuarios a todo el sistema.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <Label>Estado</Label>
          <Select value={cfg.servicio_estado} onValueChange={(v) => setCfg({ ...cfg, servicio_estado: v as ConfigCfg['servicio_estado'] })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="activo"><CheckCircle2 className="text-emerald-600" />Activo</SelectItem>
              <SelectItem value="pausado"><Pause className="text-amber-600" />Pausado</SelectItem>
              <SelectItem value="suspendido"><Ban className="text-destructive" />Suspendido</SelectItem>
            </SelectContent>
          </Select>
          <p className={`flex items-center gap-1.5 text-xs ${estadoInfo[cfg.servicio_estado].color}`}>
            <Icon className="size-3.5 shrink-0" />{estadoInfo[cfg.servicio_estado].desc}
          </p>
        </div>
        <Field label="Mensaje (opcional)" value={cfg.servicio_mensaje} onChange={(v) => setCfg({ ...cfg, servicio_mensaje: v })} />
        <div className="col-span-full">
          <Button disabled={saving} onClick={() => guardar('/api/config/servicio', {
            servicio_estado: cfg.servicio_estado, servicio_mensaje: cfg.servicio_mensaje,
          })}>
            <Check />{saving ? 'Guardando…' : 'Guardar estado'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function TicketTab({ cfg, setCfg, saving, guardar }: {
  cfg: ConfigCfg; setCfg: (c: ConfigCfg) => void; saving: boolean; guardar: GuardarFn
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base"><Printer className="size-4" />Impresora de tickets</CardTitle>
        <CardDescription>Configurá cómo se imprime el ticket en impresoras de rollo (Epson TM, Star, Bixolon, etc.).</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <Label>Ancho del rollo</Label>
          <Select value={cfg.ticket_ancho_mm} onValueChange={(v) => setCfg({ ...cfg, ticket_ancho_mm: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="80">80 mm (estándar)</SelectItem>
              <SelectItem value="58">58 mm (mini)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-1.5">
          <Label>Tamaño de fuente</Label>
          <Select value={cfg.ticket_fuente_size} onValueChange={(v) => setCfg({ ...cfg, ticket_fuente_size: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7 pt — muy pequeño</SelectItem>
              <SelectItem value="8">8 pt — pequeño</SelectItem>
              <SelectItem value="9">9 pt — normal (recomendado)</SelectItem>
              <SelectItem value="10">10 pt — grande</SelectItem>
              <SelectItem value="11">11 pt — muy grande</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Field label="Texto al pie" value={cfg.ticket_pie} onChange={(v) => setCfg({ ...cfg, ticket_pie: v })} />
        <div className="grid content-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={cfg.ticket_mostrar_logo === '1'} onChange={(e) => setCfg({ ...cfg, ticket_mostrar_logo: e.target.checked ? '1' : '0' })} />
            Mostrar logo de la empresa
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={cfg.ticket_linea_corte === '1'} onChange={(e) => setCfg({ ...cfg, ticket_linea_corte: e.target.checked ? '1' : '0' })} />
            Imprimir línea de corte al final
          </label>
        </div>
        <div className="col-span-full">
          <Button disabled={saving} onClick={() => guardar('/api/config/ticket', {
            ticket_ancho_mm: cfg.ticket_ancho_mm, ticket_fuente_size: cfg.ticket_fuente_size,
            ticket_mostrar_logo: cfg.ticket_mostrar_logo === '1', ticket_linea_corte: cfg.ticket_linea_corte === '1',
            ticket_pie: cfg.ticket_pie,
          })}>
            <Check />{saving ? 'Guardando…' : 'Guardar configuración'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function CategoriasTab() {
  const [productoCats, setProductoCats] = useState<CategoriaProducto[]>([])
  const [egresoCats, setEgresoCats] = useState<CategoriaEgreso[]>([])
  const [nuevoProducto, setNuevoProducto] = useState('')
  const [nuevoEgreso, setNuevoEgreso] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { cargar() }, [])

  async function cargar() {
    try {
      const [p, e] = await Promise.all([
        api.get<CategoriaProducto[]>('/api/productos/categorias'),
        api.get<CategoriaEgreso[]>('/api/egresos/categorias'),
      ])
      setProductoCats(p)
      setEgresoCats(e)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Error de conexión.')
    }
  }

  async function eliminarProducto(c: CategoriaProducto) {
    if (!window.confirm(`¿Eliminar la categoría «${c.nombre}»?`)) return
    setProductoCats(await api.del<CategoriaProducto[]>(`/api/productos/categorias/${c.id}`))
  }

  async function eliminarEgreso(c: CategoriaEgreso) {
    if (!window.confirm(`¿Eliminar la categoría «${c.nombre}»?`)) return
    setEgresoCats(await api.del<CategoriaEgreso[]>(`/api/egresos/categorias/${c.id}`))
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {error && <p className="col-span-full text-sm text-destructive">{error}</p>}
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Package className="size-4" />Categorías de producto</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <div className="flex gap-2">
            <Input value={nuevoProducto} onChange={(e) => setNuevoProducto(e.target.value)} placeholder="Ej: Electrónica, Ropa, Servicios…" />
            <Button onClick={async () => {
              if (!nuevoProducto.trim()) return
              setProductoCats(await api.post<CategoriaProducto[]>('/api/productos/categorias', { nombre: nuevoProducto }))
              setNuevoProducto('')
            }}><Plus />Agregar</Button>
          </div>
          {productoCats.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">No hay categorías creadas aún.</p>
          ) : (
            <ul className="divide-y">
              {productoCats.map((c) => (
                <li key={c.id} className="flex items-center justify-between py-1.5 text-sm">
                  <span className="flex items-center gap-2"><Tag className="size-3.5 text-muted-foreground" />{c.nombre}</span>
                  <Button size="sm" variant="ghost" onClick={() => eliminarProducto(c)}><Trash2 /></Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Receipt className="size-4" />Categorías de egreso</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <div className="flex gap-2">
            <Input value={nuevoEgreso} onChange={(e) => setNuevoEgreso(e.target.value)} placeholder="Ej: Alquiler, Servicios, Sueldos…" />
            <Button onClick={async () => {
              if (!nuevoEgreso.trim()) return
              setEgresoCats(await api.post<CategoriaEgreso[]>('/api/egresos/categorias', { nombre: nuevoEgreso }))
              setNuevoEgreso('')
            }}><Plus />Agregar</Button>
          </div>
          {egresoCats.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">No hay categorías creadas aún.</p>
          ) : (
            <ul className="divide-y">
              {egresoCats.map((c) => (
                <li key={c.id} className="flex items-center justify-between py-1.5 text-sm">
                  <span className="flex items-center gap-2"><Tag className="size-3.5 text-muted-foreground" />{c.nombre}</span>
                  <Button size="sm" variant="ghost" onClick={() => eliminarEgreso(c)}><Trash2 /></Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function DatosTab({ saving, setSaving, setError, describeError }: {
  saving: boolean; setSaving: (v: boolean) => void
  setError: (v: string | null) => void; describeError: (err: unknown) => string
}) {
  const [backups, setBackups] = useState<Backup[]>([])
  const [restoreMsg, setRestoreMsg] = useState<string | null>(null)

  useEffect(() => { cargar() }, [])

  async function cargar() {
    try {
      setBackups(await api.get<Backup[]>('/api/config/backups'))
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function restaurar(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!window.confirm('¿Estás seguro? Se reemplazarán TODOS los datos actuales.')) {
      e.target.value = ''
      return
    }
    setSaving(true)
    setError(null)
    setRestoreMsg(null)
    try {
      const form = new FormData()
      form.append('backup_file', file)
      await api.postForm('/api/config/restore-db', form)
      setRestoreMsg('Base de datos restaurada correctamente. Se guardó un backup automático antes de reemplazar.')
      await cargar()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
      e.target.value = ''
    }
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base"><Download className="size-4" />Backup manual</CardTitle>
          <CardDescription>Descargá una copia completa de la base de datos en este momento.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild className="w-full">
            <a href="/config/backup-db" download><Download />Descargar backup ahora</a>
          </Button>
          <p className="mt-2 text-xs text-muted-foreground">El archivo .db contiene todos tus datos: clientes, facturas, ventas, caja, etc.</p>
        </CardContent>
      </Card>

      <Card className="border-amber-500/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base text-amber-600 dark:text-amber-400"><Upload className="size-4" />Restaurar base de datos</CardTitle>
          <CardDescription>Esto reemplaza todos los datos actuales con el backup seleccionado.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="grid gap-1.5">
            <Label>Archivo de backup (.db)</Label>
            <Input type="file" accept=".db" disabled={saving} onChange={restaurar} />
          </div>
          {restoreMsg && <p className="text-sm text-emerald-600 dark:text-emerald-400">{restoreMsg}</p>}
        </CardContent>
      </Card>

      <Card className="sm:col-span-2">
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Database className="size-4" />Backups automáticos guardados en el servidor</CardTitle></CardHeader>
        <CardContent>
          {backups.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">Sin backups automáticos todavía. Se generan automáticamente antes de cada restauración.</p>
          ) : (
            <>
              <ul className="divide-y">
                {backups.map((b) => (
                  <li key={b.filename} className="flex items-center justify-between py-2 text-sm">
                    <div>
                      <p className="font-mono font-medium">{b.filename}</p>
                      <p className="text-muted-foreground">{b.mtime} — {b.size_mb} MB</p>
                    </div>
                    <Button asChild size="sm" variant="outline">
                      <a href={`/config/backup-db/${b.filename}`} download><Download />Descargar</a>
                    </Button>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-muted-foreground">Se conservan los últimos 10 backups automáticos.</p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function Field({ label, value, onChange, type = 'text' }: {
  label: string; value: string; onChange: (v: string) => void; type?: string
}) {
  return (
    <div className="grid gap-1.5">
      <Label>{label}</Label>
      <Input type={type} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  )
}
