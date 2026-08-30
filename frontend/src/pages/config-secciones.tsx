/** Las tres secciones que este producto NO comparte con el kit.
 *
 *  El resto de la pantalla —Empresa, MercadoPago, ARCA, Datos / Backup, la
 *  barra de pestañas, la sub-navegación de Integraciones, el botón de *Backup
 *  rápido* y los tutoriales— vive en `libra-ui/Configuracion`. Este archivo es
 *  lo que queda del `Config.tsx` de 987 líneas del que salió esa pantalla.
 *
 *  🔴 **La copia única vive en el kit, no acá.** Es el punto del pedido del
 *  humano del 2026-08-29: mientras la versión buena viviera adentro de este
 *  producto, arreglarla no arreglaba a los otros siete.
 */
import { useEffect, useState, type ReactNode } from 'react'
import { Check, Mail, Package, Plus, Printer, Receipt, Save, Send, Tag, Trash2 } from 'lucide-react'
import { TutorialGmail } from 'libra-ui/Configuracion'
import { PasswordInput } from 'libra-ui/PasswordInput'

import { api, ApiError, type CategoriaEgreso } from '../api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { ConfirmDialog } from '@/components/confirm-dialog'

type CategoriaProducto = { id: number; nombre: string }

function describeError(err: unknown): string {
  if (err instanceof ApiError) return err.detail
  return 'Error de conexión.'
}

/** 🔴 La etiqueta va asociada al input con `htmlFor`/`id`, cosa que el `Field`
 *  original de esta pantalla no hacia. No es cosmetico: sin eso un lector de
 *  pantalla no anuncia que campo esta enfocado, y `getByLabelText` no encuentra
 *  el control --que es como se descubrio, al escribirle a esta pantalla su
 *  primer test--. El `id` sale del label, normalizado. */
function idDe(label: string): string {
  return `cfg-${label.toLowerCase().normalize('NFD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`
}

function Campo({ label, value, onChange, type = 'text', marcador }: {
  label: string; value: string; onChange: (v: string) => void
  type?: string; marcador?: string
}) {
  const id = idDe(label)
  const campo = type === 'password'
    ? <PasswordInput id={id} value={value} placeholder={marcador} onChange={(e) => onChange(e.target.value)} />
    : <Input id={id} type={type} value={value} placeholder={marcador} onChange={(e) => onChange(e.target.value)} />
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      {campo}
    </div>
  )
}


/** El correo saliente de ESTE producto.
 *
 *  🔴 **No se usa la sección de correo del kit, y es a propósito.** Esta
 *  instancia tiene DOS configuraciones de SMTP y no son la misma:
 *
 *  - `config.json` (`email_smtp_*`), que es la que lee `helpers/email_helper.py`
 *    — o sea **la que de verdad manda los mails** — y la que prueba
 *    `GET /api/email/probar`;
 *  - la base de libraauth, detrás de `/api/config/smtp`, que en este producto
 *    no la lee nadie para enviar.
 *
 *  La sección del kit apunta a la segunda. Cambiarla acá dejaría la pantalla
 *  configurando un SMTP que no envía nada: el cliente carga su contraseña de
 *  aplicación, la pantalla dice "Guardado", y los comprobantes siguen sin
 *  salir.
 *
 *  Unificar los dos stores es un trabajo aparte, decidido con el humano el
 *  2026-08-30: primero se normaliza el resto de la pantalla en los ocho
 *  productos, y después se ve si los dos se pueden juntar.
 *
 *  Lo que sí viene del kit es el **tutorial**, que es lo que faltaba en los
 *  otros seis y acá ya estaba: ahora es el mismo texto para todos.
 */
type Correo = {
  email_smtp_host: string
  email_smtp_port: string
  email_smtp_user: string
  email_from: string
  email_from_name: string
  /** Si hay una guardada. La contrasena NO vuelve del servidor. */
  email_smtp_password_definida: boolean
}

export function EmailCard() {
  const [cfg, setCfg] = useState<Correo | null>(null)
  // 🔴 Aparte del resto y arrancando vacia: la contrasena no vuelve del
  // servidor, y vacia significa "no la toques" del lado del `PUT`. Si viviera
  // en `cfg` y se mandara tal como se ve, guardar el remitente la borraria.
  const [password, setPassword] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [probando, setProbando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  useEffect(() => { void cargar() }, [])

  async function cargar() {
    try {
      setCfg(await api.get<Correo>('/api/config/email'))
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function guardar() {
    if (!cfg) return
    setGuardando(true)
    setError(null)
    setAviso(null)
    try {
      await api.put('/api/config/email', {
        email_smtp_host: cfg.email_smtp_host, email_smtp_port: cfg.email_smtp_port,
        email_smtp_user: cfg.email_smtp_user, email_smtp_password: password,
        email_from: cfg.email_from, email_from_name: cfg.email_from_name,
      })
      setPassword('')
      setAviso('Guardado.')
      await cargar()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setGuardando(false)
    }
  }

  async function probar() {
    setProbando(true)
    setAviso(null)
    setError(null)
    try {
      const r = await api.get<{ ok: boolean; host?: string; error?: string }>('/api/email/probar')
      if (r.ok) setAviso(`Conectado — ${r.host}`)
      else setError(r.error ?? 'Error')
    } catch (err) {
      setError(describeError(err))
    } finally {
      setProbando(false)
    }
  }

  if (!cfg) {
    return <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Mail className="size-4" />Email (SMTP)
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <div className="col-span-full"><TutorialGmail producto="Contalibra" /></div>
        <Campo label="Host SMTP" value={cfg.email_smtp_host} onChange={(v) => setCfg({ ...cfg, email_smtp_host: v })} />
        <Campo label="Puerto" value={cfg.email_smtp_port} onChange={(v) => setCfg({ ...cfg, email_smtp_port: v })} />
        <Campo label="Usuario" value={cfg.email_smtp_user} onChange={(v) => setCfg({ ...cfg, email_smtp_user: v })} />
        <Campo
          label="Contraseña" type="password" value={password} onChange={setPassword}
          marcador={cfg.email_smtp_password_definida
            ? 'Guardada — dejala vacía para no cambiarla'
            : 'La contraseña de aplicación de 16 caracteres'}
        />
        <Campo label="Remitente" value={cfg.email_from} onChange={(v) => setCfg({ ...cfg, email_from: v })} />
        <Campo label="Nombre del remitente" value={cfg.email_from_name} onChange={(v) => setCfg({ ...cfg, email_from_name: v })} />
        <div className="col-span-full flex flex-wrap items-center gap-3">
          <Button disabled={guardando} onClick={() => void guardar()}>
            <Save />{guardando ? 'Guardando…' : 'Guardar email'}
          </Button>
          {cfg.email_smtp_host && cfg.email_smtp_user && (
            <Button type="button" variant="outline" disabled={probando} onClick={() => void probar()}>
              <Send />{probando ? 'Probando…' : 'Probar conexión'}
            </Button>
          )}
          {error && <span className="text-sm text-destructive">{error}</span>}
          {aviso && <span className="text-sm text-muted-foreground">{aviso}</span>}
        </div>
      </CardContent>
    </Card>
  )
}


/** La impresora de tickets de rollo. Es de este producto: MedLibra no imprime
 *  comandas y LibraDesk no tiene mostrador. */
type Ticket = {
  ticket_ancho_mm: string
  ticket_fuente_size: string
  ticket_mostrar_logo: string
  ticket_linea_corte: string
  ticket_pie: string
}

export function TicketCard() {
  const [cfg, setCfg] = useState<Ticket | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aviso, setAviso] = useState<string | null>(null)

  useEffect(() => { void cargar() }, [])

  async function cargar() {
    try {
      setCfg(await api.get<Ticket>('/api/config/ticket'))
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function guardar() {
    if (!cfg) return
    setGuardando(true)
    setError(null)
    setAviso(null)
    try {
      await api.put('/api/config/ticket', {
        ticket_ancho_mm: cfg.ticket_ancho_mm, ticket_fuente_size: cfg.ticket_fuente_size,
        ticket_mostrar_logo: cfg.ticket_mostrar_logo === '1',
        ticket_linea_corte: cfg.ticket_linea_corte === '1',
        ticket_pie: cfg.ticket_pie,
      })
      setAviso('Guardado.')
      await cargar()
    } catch (err) {
      setError(describeError(err))
    } finally {
      setGuardando(false)
    }
  }

  if (!cfg) {
    return <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Printer className="size-4" />Impresora de tickets
        </CardTitle>
        <CardDescription>
          Configurá cómo se imprime el ticket en impresoras de rollo (Epson TM, Star, Bixolon, etc.).
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label>Ancho del rollo</Label>
          <Select value={cfg.ticket_ancho_mm} onValueChange={(v) => setCfg({ ...cfg, ticket_ancho_mm: v })}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="80">80 mm (estándar)</SelectItem>
              <SelectItem value="58">58 mm (mini)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="grid gap-2">
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
        <Campo label="Texto al pie" value={cfg.ticket_pie} onChange={(v) => setCfg({ ...cfg, ticket_pie: v })} />
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
        <div className="col-span-full flex flex-wrap items-center gap-3">
          <Button disabled={guardando} onClick={() => void guardar()}>
            <Check />{guardando ? 'Guardando…' : 'Guardar configuración'}
          </Button>
          {error && <span className="text-sm text-destructive">{error}</span>}
          {aviso && <span className="text-sm text-muted-foreground">{aviso}</span>}
        </div>
      </CardContent>
    </Card>
  )
}


/** Las categorías de producto y de egreso.
 *
 *  No estaban en la vieja `config.html` —eran páginas standalone linkeadas
 *  desde Egresos y Productos— y se mantienen acá por practicidad de la SPA.
 */
export function CategoriasCard() {
  const [productoCats, setProductoCats] = useState<CategoriaProducto[]>([])
  const [egresoCats, setEgresoCats] = useState<CategoriaEgreso[]>([])
  const [nuevoProducto, setNuevoProducto] = useState('')
  const [nuevoEgreso, setNuevoEgreso] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [confirmProducto, setConfirmProducto] = useState<CategoriaProducto | null>(null)
  const [confirmEgreso, setConfirmEgreso] = useState<CategoriaEgreso | null>(null)

  useEffect(() => { void cargar() }, [])

  async function cargar() {
    try {
      const [p, e] = await Promise.all([
        api.get<CategoriaProducto[]>('/api/productos/categorias'),
        api.get<CategoriaEgreso[]>('/api/egresos/categorias'),
      ])
      setProductoCats(p)
      setEgresoCats(e)
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {error && <p className="col-span-full text-sm text-destructive">{error}</p>}
      <Lista
        titulo="Categorías de producto" icono={<Package className="size-4" />}
        marcador="Ej: Electrónica, Ropa, Servicios…"
        items={productoCats} nuevo={nuevoProducto} setNuevo={setNuevoProducto}
        alAgregar={async (nombre) => setProductoCats(
          await api.post<CategoriaProducto[]>('/api/productos/categorias', { nombre }))}
        alBorrar={(c) => setConfirmProducto(c as CategoriaProducto)}
      />
      <Lista
        titulo="Categorías de egreso" icono={<Receipt className="size-4" />}
        marcador="Ej: Alquiler, Servicios, Sueldos…"
        items={egresoCats} nuevo={nuevoEgreso} setNuevo={setNuevoEgreso}
        alAgregar={async (nombre) => setEgresoCats(
          await api.post<CategoriaEgreso[]>('/api/egresos/categorias', { nombre }))}
        alBorrar={(c) => setConfirmEgreso(c as CategoriaEgreso)}
      />

      <ConfirmDialog
        open={confirmProducto !== null}
        onOpenChange={(o) => !o && setConfirmProducto(null)}
        title={`¿Eliminar la categoría «${confirmProducto?.nombre ?? ''}»?`}
        onConfirm={() => {
          if (confirmProducto) {
            void api.del<CategoriaProducto[]>(`/api/productos/categorias/${confirmProducto.id}`)
              .then(setProductoCats)
          }
          setConfirmProducto(null)
        }}
      />
      <ConfirmDialog
        open={confirmEgreso !== null}
        onOpenChange={(o) => !o && setConfirmEgreso(null)}
        title={`¿Eliminar la categoría «${confirmEgreso?.nombre ?? ''}»?`}
        onConfirm={() => {
          if (confirmEgreso) {
            void api.del<CategoriaEgreso[]>(`/api/egresos/categorias/${confirmEgreso.id}`)
              .then(setEgresoCats)
          }
          setConfirmEgreso(null)
        }}
      />
    </div>
  )
}

/** Las dos listas de categorías son la misma tarjeta con otro endpoint: estaban
 *  escritas dos veces, con el mismo marcado copiado. */
function Lista({ titulo, icono, marcador, items, nuevo, setNuevo, alAgregar, alBorrar }: {
  titulo: string
  icono: ReactNode
  marcador: string
  items: { id: number; nombre: string }[]
  nuevo: string
  setNuevo: (v: string) => void
  alAgregar: (nombre: string) => Promise<void>
  alBorrar: (c: { id: number; nombre: string }) => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">{icono}{titulo}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3">
        <div className="flex gap-2">
          <Input value={nuevo} onChange={(e) => setNuevo(e.target.value)} placeholder={marcador} />
          <Button onClick={async () => {
            if (!nuevo.trim()) return
            await alAgregar(nuevo)
            setNuevo('')
          }}><Plus />Agregar</Button>
        </div>
        {items.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">No hay categorías creadas aún.</p>
        ) : (
          <ul className="divide-y">
            {items.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-1.5 text-sm">
                <span className="flex items-center gap-2"><Tag className="size-3.5 text-muted-foreground" />{c.nombre}</span>
                <Button size="sm" variant="ghost" onClick={() => alBorrar(c)}><Trash2 /></Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
