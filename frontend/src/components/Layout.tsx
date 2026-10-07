import { Store } from 'lucide-react'
import { ICONOS } from 'libra-ui/iconos-identidad'
import { createLayout, type NavSection } from 'libra-ui/Layout'
import { WORDMARK } from '@/branding'
import { useAuth } from '../context/AuthContext'
import type { User } from '../api'

// Mismo orden y agrupamiento que el sidebar Jinja2 viejo
// (web/templates/base.html, commit 1a8808c) -- ver
// wiki/entities/contalibra.md, auditoria de regresion funcional.
const NAV_SECTIONS: NavSection<User>[] = [
  {
    items: [{ to: '/dashboard', label: 'Dashboard', icon: ICONOS.dashboard }],
  },
  {
    label: 'Ventas',
    items: [
      { to: '/facturas', label: 'Comprobantes', icon: ICONOS.comprobantes, module: 'facturacion' },
      // Sin `module`: un recibo nace de una factura, de una venta o de un pago
      // de cuenta corriente, así que gatearlo por uno solo de esos módulos
      // escondería la reimpresión de los otros dos. Mismo criterio que su
      // router (ver web/api/recibos.py).
      { to: '/recibos', label: 'Recibos', icon: ICONOS.recibos },
      { to: '/presupuestos', label: 'Presupuestos', icon: ICONOS.presupuestos, module: 'presupuestos' },
      { to: '/remitos', label: 'Remitos', icon: ICONOS.remitos, module: 'remitos' },
      { to: '/ventas', label: 'Ventas POS', icon: ICONOS.ventas, module: 'ventas' },
      {
        to: '/clientes', label: 'Clientes', icon: ICONOS.clientes, module: 'clientes',
        children: [{ to: '/cuenta-corriente', label: 'Cuenta Corriente', module: 'cuenta_corriente', icon: ICONOS.cuentaCorriente }],
      },
    ],
  },
  {
    label: 'Compras',
    items: [
      { to: '/egresos', label: 'Egresos', icon: ICONOS.egresos, module: 'egresos' },
      { to: '/proveedores', label: 'Proveedores', icon: ICONOS.proveedores, module: 'proveedores' },
    ],
  },
  {
    label: 'Inventario',
    items: [
      {
        to: '/productos', label: 'Productos', icon: ICONOS.productos, module: 'productos',
        children: [{ to: '/listas-precio', label: 'Listas de precios', module: 'listas_precio', icon: ICONOS.listasDePrecio }],
      },
      { to: '/stock', label: 'Stock', icon: ICONOS.stock, module: 'stock' },
      { to: '/depositos', label: 'Depósitos', icon: ICONOS.depositos, module: 'depositos' },
    ],
  },
  {
    label: 'Caja & Tesorería',
    items: [
      {
        to: '/caja', label: 'Caja', icon: ICONOS.caja, module: 'caja',
        children: [
          { to: '/turnos', label: 'Turnos', icon: ICONOS.turnosDeCaja },
          { to: '/cajas', label: 'Gestionar cajas', module: 'cajas', icon: ICONOS.cajas },
        ],
      },
      { to: '/tesoreria', label: 'Cuentas bancarias', icon: ICONOS.tesoreria, module: 'tesoreria', adminOnly: true },
    ],
  },
  {
    items: [{
      to: '/mp-bandeja', label: 'Pagos MercadoPago', icon: ICONOS.pagosMercadoPago,
      badge: (u) => u.mp_pending_count || undefined,
    }],
  },
  {
    items: [{
      // Lo que otro producto de la familia (hoy LibraDesk) dejó para facturar
      // acá. Sin badge la pantalla existe y nadie la abre: nada avisa que
      // llegó algo de afuera.
      to: '/comprobantes-pendientes', label: 'Comprobantes a facturar', icon: ICONOS.comprobantesAFacturar,
      adminOnly: true,
      badge: (u) => u.comprobantes_pendientes_count || undefined,
    }],
  },
  {
    label: 'Reportes',
    items: [
      {
        to: '/reportes', label: 'Reportes', icon: ICONOS.reportes, module: 'reportes',
        children: [{ to: '/reportes/caja-medios', label: 'Caja por medio', module: 'reportes', icon: ICONOS.cajaPorMedio }],
      },
      { to: '/libros-iva', label: 'Libros IVA', icon: ICONOS.librosDeIva, module: 'libros_iva', adminOnly: true },
    ],
  },
  {
    items: [{ to: '/config', label: 'Configuración', icon: ICONOS.configuracion }],
  },
  {
    label: 'Administración',
    items: [
      { to: '/usuarios', label: 'Usuarios', icon: ICONOS.usuarios, adminOnly: true },
      { to: '/logs', label: 'Logs', icon: ICONOS.logDeActividad, adminOnly: true },
    ],
  },
]

export const Layout = createLayout<User>({
  productName: 'Contalibra',
  productInitial: 'C',
  // La marca (ícono + color del producto) la dibuja libra-ui con `producto` (ADR-033) y el nombre va en Montserrat Bold. Las clases del
  // nombre salen de `@/branding`, el mismo archivo que usa el login: es lo que garantiza que las dos pantallas escriban "Contalibra" igual.
  producto: 'contalibra',
  // 🔴 El interlineado va PEGADO al tamano (`/[17px]`) y no como `leading-*`
  // aparte: en Tailwind v4 una utilidad de tamano emite tambien `line-height`,
  // asi que el `leading-none` que libra-ui pone por defecto perderia contra
  // este `text-[15px]` y el nombre se quedaria con 22,5 px de caja.
  // 17 = 32 (el alto de `MarcaProducto`) menos los 15 de la linea de la empresa.
  wordmarkClassName: `${WORDMARK} text-[15px]/[17px]`,
  navSections: NAV_SECTIONS,
  icon: Store,
  homeTo: '/dashboard',
  accountTo: '/mi-cuenta',
  // Ya no se pasa `topbar`: desde libra-ui v0.19.0 la barra no existe para
  // ningún producto, así que la opción se fue. El render de acá no cambia --
  // Contalibra venía pasando `topbar: false` desde que la barra se sacó.
  useAuth,
  hasModule: (u, m) => u.modulos.includes(m),
  getUserName: (u) => u.nombre,
  getUserSubtitle: (u) => u.empresa_nombre,
})
