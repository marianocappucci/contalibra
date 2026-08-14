import {
  BarChart3, BookOpen, BookText, Boxes, Calculator, Clock, CreditCard, FileText, History,
  Inbox, Landmark, LayoutDashboard, Package, Receipt, ReceiptText, Settings, ShoppingBag,
  ShoppingCart, SquareStack, Store, Tag, Truck, UserCog, Users, Wallet, Warehouse,
} from 'lucide-react'
import { createLayout, type NavSection } from 'libra-ui/Layout'
import { useAuth } from '../context/AuthContext'
import type { User } from '../api'

// Mismo orden y agrupamiento que el sidebar Jinja2 viejo
// (web/templates/base.html, commit 1a8808c) -- ver
// wiki/entities/contalibra.md, auditoria de regresion funcional.
const NAV_SECTIONS: NavSection<User>[] = [
  {
    items: [{ to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'Ventas',
    items: [
      { to: '/facturas', label: 'Comprobantes', icon: Receipt, module: 'facturacion' },
      // Sin `module`: un recibo nace de una factura, de una venta o de un pago
      // de cuenta corriente, así que gatearlo por uno solo de esos módulos
      // escondería la reimpresión de los otros dos. Mismo criterio que su
      // router (ver web/api/recibos.py).
      { to: '/recibos', label: 'Recibos', icon: ReceiptText },
      { to: '/presupuestos', label: 'Presupuestos', icon: Calculator, module: 'presupuestos' },
      { to: '/remitos', label: 'Remitos', icon: FileText, module: 'remitos' },
      { to: '/ventas', label: 'Ventas POS', icon: ShoppingCart, module: 'ventas' },
      {
        to: '/clientes', label: 'Clientes', icon: Users, module: 'clientes',
        children: [{ to: '/cuenta-corriente', label: 'Cuenta Corriente', module: 'cuenta_corriente', icon: BookOpen }],
      },
    ],
  },
  {
    label: 'Compras',
    items: [
      { to: '/egresos', label: 'Egresos', icon: ShoppingBag, module: 'egresos' },
      { to: '/proveedores', label: 'Proveedores', icon: Truck, module: 'proveedores' },
    ],
  },
  {
    label: 'Inventario',
    items: [
      {
        to: '/productos', label: 'Productos', icon: Package, module: 'productos',
        children: [{ to: '/listas-precio', label: 'Listas de precios', module: 'listas_precio', icon: Tag }],
      },
      { to: '/stock', label: 'Stock', icon: Boxes, module: 'stock' },
      { to: '/depositos', label: 'Depósitos', icon: Warehouse, module: 'depositos' },
    ],
  },
  {
    label: 'Caja & Tesorería',
    items: [
      {
        to: '/caja', label: 'Caja', icon: SquareStack, module: 'caja',
        children: [
          { to: '/turnos', label: 'Turnos', icon: Clock },
          { to: '/cajas', label: 'Gestionar cajas', module: 'cajas', icon: SquareStack },
        ],
      },
      { to: '/tesoreria', label: 'Cuentas bancarias', icon: Landmark, module: 'tesoreria', adminOnly: true },
    ],
  },
  {
    items: [{
      to: '/mp-bandeja', label: 'Pagos MercadoPago', icon: CreditCard,
      badge: (u) => u.mp_pending_count || undefined,
    }],
  },
  {
    items: [{
      // Lo que otro producto de la familia (hoy LibraDesk) dejó para facturar
      // acá. Sin badge la pantalla existe y nadie la abre: nada avisa que
      // llegó algo de afuera.
      to: '/comprobantes-pendientes', label: 'Comprobantes a facturar', icon: Inbox,
      adminOnly: true,
      badge: (u) => u.comprobantes_pendientes_count || undefined,
    }],
  },
  {
    label: 'Reportes',
    items: [
      {
        to: '/reportes', label: 'Reportes', icon: BarChart3, module: 'reportes',
        children: [{ to: '/reportes/caja-medios', label: 'Caja por medio', module: 'reportes', icon: Wallet }],
      },
      { to: '/libros-iva', label: 'Libros IVA', icon: BookText, module: 'libros_iva', adminOnly: true },
    ],
  },
  {
    items: [{ to: '/config', label: 'Configuración', icon: Settings }],
  },
  {
    label: 'Administración',
    items: [
      { to: '/usuarios', label: 'Usuarios', icon: UserCog, adminOnly: true },
      { to: '/logs', label: 'Logs', icon: History, adminOnly: true },
    ],
  },
]

export const Layout = createLayout<User>({
  productName: 'Contalibra',
  productInitial: 'C',
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
