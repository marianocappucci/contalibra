import { useEffect, useState, type ChangeEvent } from 'react'
import { api, ApiError, type ArcaConfig, type Backup, type CategoriaEgreso, type ConfigCfg } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'

type CategoriaProducto = { id: number; nombre: string }

const TABS = [
  { id: 'empresa', label: 'Empresa' },
  { id: 'mp', label: 'MercadoPago' },
  { id: 'email', label: 'Email' },
  { id: 'arca', label: 'ARCA' },
  { id: 'servicio', label: 'Servicio' },
  { id: 'ticket', label: 'Ticket' },
  { id: 'categorias', label: 'Categorías' },
  { id: 'datos', label: 'Datos' },
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
      <h2 className="text-lg font-semibold">Configuración</h2>

      <div className="flex flex-wrap gap-1 border-b pb-2">
        {TABS.map((t) => (
          <Button
            key={t.id} size="sm" variant={tab === t.id ? 'default' : 'ghost'}
            onClick={() => { setTab(t.id); setSaved(null); setError(null) }}
          >
            {t.label}
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
      <CardHeader><CardTitle className="text-base">Datos de la empresa</CardTitle></CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <Field label="Nombre" value={cfg.empresa_nombre} onChange={(v) => setCfg({ ...cfg, empresa_nombre: v })} />
        <Field label="CUIT" value={cfg.empresa_cuit} onChange={(v) => setCfg({ ...cfg, empresa_cuit: v })} />
        <Field label="Dirección" value={cfg.empresa_direccion} onChange={(v) => setCfg({ ...cfg, empresa_direccion: v })} />
        <Field label="Teléfono" value={cfg.empresa_telefono} onChange={(v) => setCfg({ ...cfg, empresa_telefono: v })} />
        <Field label="Email" value={cfg.empresa_email} onChange={(v) => setCfg({ ...cfg, empresa_email: v })} />
        <Field label="Ingresos Brutos" value={cfg.empresa_iibb} onChange={(v) => setCfg({ ...cfg, empresa_iibb: v })} />
        <Field label="Condición de IVA" value={cfg.empresa_iva_condition} onChange={(v) => setCfg({ ...cfg, empresa_iva_condition: v })} />
        <Field label="Inicio de actividades" value={cfg.empresa_inicio_actividades} onChange={(v) => setCfg({ ...cfg, empresa_inicio_actividades: v })} />
        <div className="grid gap-1.5">
          <Label>Logo (PNG o JPG)</Label>
          <Input type="file" accept=".png,.jpg,.jpeg" onChange={handleLogo} disabled={saving} />
        </div>
        <div className="col-span-full">
          <Button disabled={saving} onClick={() => guardar('/api/config/empresa', {
            empresa_nombre: cfg.empresa_nombre, empresa_direccion: cfg.empresa_direccion,
            empresa_cuit: cfg.empresa_cuit, empresa_telefono: cfg.empresa_telefono,
            empresa_email: cfg.empresa_email, empresa_iibb: cfg.empresa_iibb,
            empresa_iva_condition: cfg.empresa_iva_condition,
            empresa_inicio_actividades: cfg.empresa_inicio_actividades,
          })}>
            {saving ? 'Guardando…' : 'Guardar'}
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

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">MercadoPago</CardTitle></CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <Field label="Access Token" type="password" value={cfg.mp_access_token} onChange={(v) => setCfg({ ...cfg, mp_access_token: v })} />
        <Field label="Webhook Secret" type="password" value={cfg.mp_webhook_secret} onChange={(v) => setCfg({ ...cfg, mp_webhook_secret: v })} />
        <Field label="Descripción del cobro" value={cfg.mp_concepto_descripcion} onChange={(v) => setCfg({ ...cfg, mp_concepto_descripcion: v })} />
        <Field label="Alícuota IVA (ej. 0.21)" value={cfg.mp_iva_rate} onChange={(v) => setCfg({ ...cfg, mp_iva_rate: v })} />
        <Field label="User ID (QR)" value={cfg.mp_user_id} onChange={(v) => setCfg({ ...cfg, mp_user_id: v })} />
        <Field label="POS ID (QR)" value={cfg.mp_pos_id} onChange={(v) => setCfg({ ...cfg, mp_pos_id: v })} />
        <div className="col-span-full flex items-center gap-3">
          <Button disabled={saving} onClick={() => guardar('/api/config/mp', {
            mp_access_token: cfg.mp_access_token, mp_webhook_secret: cfg.mp_webhook_secret,
            mp_concepto_descripcion: cfg.mp_concepto_descripcion, mp_iva_rate: cfg.mp_iva_rate,
            mp_user_id: cfg.mp_user_id, mp_pos_id: cfg.mp_pos_id,
          })}>
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
          <Button type="button" variant="outline" disabled={probando} onClick={probar}>
            {probando ? 'Probando…' : 'Probar conexión'}
          </Button>
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
      <CardHeader><CardTitle className="text-base">Email (SMTP)</CardTitle></CardHeader>
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
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
          <Button type="button" variant="outline" disabled={probando} onClick={probar}>
            {probando ? 'Probando…' : 'Probar conexión'}
          </Button>
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
      <CardHeader><CardTitle className="text-base">ARCA (facturación electrónica)</CardTitle></CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <Field label="CUIT" value={a.cuit} onChange={(v) => setArca({ ...a, cuit: v })} />
        <Field label="Punto de venta" value={String(a.punto_venta)} onChange={(v) => setArca({ ...a, punto_venta: Number(v) || 1 })} />
        <div className="grid gap-1.5">
          <Label>Ambiente</Label>
          <Select value={a.ambiente} onValueChange={(v) => setArca({ ...a, ambiente: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="homologacion">Homologación</SelectItem>
              <SelectItem value="produccion">Producción</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Field label="Alias" value={a.alias} onChange={(v) => setArca({ ...a, alias: v })} />
        <div className="grid gap-1.5">
          <Label>Certificado (.crt)</Label>
          <Input type="file" accept=".crt,.pem" disabled={saving}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) subirArchivo(`/api/config/arca/certificados?empresa=${a.empresa}`, 'certificado', f) }} />
          {a.certificado_path && <p className="text-xs text-muted-foreground">Actual: {a.certificado_path}</p>}
        </div>
        <div className="grid gap-1.5">
          <Label>Clave privada (.key)</Label>
          <Input type="file" accept=".key,.pem" disabled={saving}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) subirArchivo(`/api/config/arca/certificados?empresa=${a.empresa}`, 'clave_privada', f) }} />
          {a.clave_path && <p className="text-xs text-muted-foreground">Actual: {a.clave_path}</p>}
        </div>
        <div className="col-span-full flex items-center gap-3">
          <Button disabled={saving} onClick={() => guardar('/api/config/arca', {
            empresa: a.empresa, cuit: a.cuit, punto_venta: a.punto_venta, ambiente: a.ambiente, alias: a.alias,
          })}>
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
          <Button type="button" variant="outline" disabled={probando} onClick={probar}>
            {probando ? 'Probando…' : 'Probar conexión'}
          </Button>
          {resultado && <span className="text-sm text-muted-foreground">{resultado}</span>}
        </div>
      </CardContent>
    </Card>
  )
}

function ServicioTab({ cfg, setCfg, saving, guardar }: {
  cfg: ConfigCfg; setCfg: (c: ConfigCfg) => void; saving: boolean; guardar: GuardarFn
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Estado del servicio</CardTitle>
        <CardDescription>Suspender bloquea el acceso de los usuarios a todo el sistema.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <Label>Estado</Label>
          <Select value={cfg.servicio_estado} onValueChange={(v) => setCfg({ ...cfg, servicio_estado: v as ConfigCfg['servicio_estado'] })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="activo">Activo</SelectItem>
              <SelectItem value="pausado">Pausado</SelectItem>
              <SelectItem value="suspendido">Suspendido</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Field label="Mensaje (opcional)" value={cfg.servicio_mensaje} onChange={(v) => setCfg({ ...cfg, servicio_mensaje: v })} />
        <div className="col-span-full">
          <Button disabled={saving} onClick={() => guardar('/api/config/servicio', {
            servicio_estado: cfg.servicio_estado, servicio_mensaje: cfg.servicio_mensaje,
          })}>
            {saving ? 'Guardando…' : 'Guardar'}
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
      <CardHeader><CardTitle className="text-base">Impresora de tickets</CardTitle></CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <Label>Ancho</Label>
          <Select value={cfg.ticket_ancho_mm} onValueChange={(v) => setCfg({ ...cfg, ticket_ancho_mm: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="58">58 mm</SelectItem>
              <SelectItem value="80">80 mm</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Field label="Tamaño de fuente" value={cfg.ticket_fuente_size} onChange={(v) => setCfg({ ...cfg, ticket_fuente_size: v })} />
        <Field label="Texto al pie" value={cfg.ticket_pie} onChange={(v) => setCfg({ ...cfg, ticket_pie: v })} />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={cfg.ticket_mostrar_logo === '1'} onChange={(e) => setCfg({ ...cfg, ticket_mostrar_logo: e.target.checked ? '1' : '0' })} />
          Mostrar logo
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={cfg.ticket_linea_corte === '1'} onChange={(e) => setCfg({ ...cfg, ticket_linea_corte: e.target.checked ? '1' : '0' })} />
          Línea de corte
        </label>
        <div className="col-span-full">
          <Button disabled={saving} onClick={() => guardar('/api/config/ticket', {
            ticket_ancho_mm: cfg.ticket_ancho_mm, ticket_fuente_size: cfg.ticket_fuente_size,
            ticket_mostrar_logo: cfg.ticket_mostrar_logo === '1', ticket_linea_corte: cfg.ticket_linea_corte === '1',
            ticket_pie: cfg.ticket_pie,
          })}>
            {saving ? 'Guardando…' : 'Guardar'}
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

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {error && <p className="col-span-full text-sm text-destructive">{error}</p>}
      <Card>
        <CardHeader><CardTitle className="text-base">Categorías de producto</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <div className="flex gap-2">
            <Input value={nuevoProducto} onChange={(e) => setNuevoProducto(e.target.value)} placeholder="Nueva categoría…" />
            <Button onClick={async () => {
              if (!nuevoProducto.trim()) return
              setProductoCats(await api.post<CategoriaProducto[]>('/api/productos/categorias', { nombre: nuevoProducto }))
              setNuevoProducto('')
            }}>Agregar</Button>
          </div>
          <ul className="space-y-1">
            {productoCats.map((c) => (
              <li key={c.id} className="flex items-center justify-between text-sm">
                {c.nombre}
                <Button size="sm" variant="ghost" onClick={async () => setProductoCats(await api.del<CategoriaProducto[]>(`/api/productos/categorias/${c.id}`))}>Eliminar</Button>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-base">Categorías de egreso</CardTitle></CardHeader>
        <CardContent className="grid gap-3">
          <div className="flex gap-2">
            <Input value={nuevoEgreso} onChange={(e) => setNuevoEgreso(e.target.value)} placeholder="Nueva categoría…" />
            <Button onClick={async () => {
              if (!nuevoEgreso.trim()) return
              setEgresoCats(await api.post<CategoriaEgreso[]>('/api/egresos/categorias', { nombre: nuevoEgreso }))
              setNuevoEgreso('')
            }}>Agregar</Button>
          </div>
          <ul className="space-y-1">
            {egresoCats.map((c) => (
              <li key={c.id} className="flex items-center justify-between text-sm">
                {c.nombre}
                <Button size="sm" variant="ghost" onClick={async () => setEgresoCats(await api.del<CategoriaEgreso[]>(`/api/egresos/categorias/${c.id}`))}>Eliminar</Button>
              </li>
            ))}
          </ul>
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
    setSaving(true)
    setError(null)
    setRestoreMsg(null)
    try {
      const form = new FormData()
      form.append('backup_file', file)
      await api.postForm('/api/config/restore-db', form)
      setRestoreMsg('Base de datos restaurada correctamente.')
      await cargar()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setSaving(false)
      e.target.value = ''
    }
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Backup y restauración</CardTitle>
          <CardDescription>Descargar la base actual, o restaurar desde un archivo .db.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <Button asChild variant="outline">
              <a href="/config/backup-db">Descargar backup actual</a>
            </Button>
            <div className="grid gap-1.5">
              <Label>Restaurar desde archivo .db</Label>
              <Input type="file" accept=".db" disabled={saving} onChange={restaurar} />
            </div>
          </div>
          {restoreMsg && <p className="text-sm text-emerald-600 dark:text-emerald-400">{restoreMsg}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Backups automáticos</CardTitle></CardHeader>
        <CardContent>
          {backups.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">Sin backups automáticos todavía.</p>
          ) : (
            <ul className="divide-y">
              {backups.map((b) => (
                <li key={b.filename} className="flex items-center justify-between py-2 text-sm">
                  <div>
                    <p className="font-medium">{b.filename}</p>
                    <p className="text-muted-foreground">{b.mtime} — {b.size_mb} MB</p>
                  </div>
                  <Button asChild size="sm" variant="outline">
                    <a href={`/config/backup-db/${b.filename}`}>Descargar</a>
                  </Button>
                </li>
              ))}
            </ul>
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
