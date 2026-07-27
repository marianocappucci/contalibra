import {
  BarChart3, BookOpen, BookText, Boxes, Calculator, Clock, CreditCard, FileText, History,
  Landmark, LayoutDashboard, Package, Receipt, Settings, ShoppingBag, ShoppingCart,
  SquareStack, Store, Tag, Truck, UserCog, Users, Wallet, Warehouse,
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
  topbar: false,
  useAuth,
  hasModule: (u, m) => u.modulos.includes(m),
  getUserName: (u) => u.nombre,
  getUserSubtitle: (u) => u.empresa_nombre,
})
