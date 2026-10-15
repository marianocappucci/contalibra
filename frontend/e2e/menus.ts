import type { Rol } from './roles'

// Lo que cada rol tiene que ver, escrito a mano e independiente del código de la SPA (`components/Layout.tsx`, con `adminOnly` y
// `module` en cada ítem): es la misma idea que la tabla de `tests/test_roles_matriz.py` de VentaLibra. Si alguien afloja un permiso
// o suma una pantalla al menú, esto se pone rojo a propósito y hay que decidir si está bien.
//
// En Contalibra los roles son tres (`ROLES` de `app/db_usuarios.py`) y la línea que importa es admin / no admin: el menú y el
// servidor distinguen al admin del resto, y `operador` y `cajero` ven y pueden lo mismo (hoy no hay nada que sólo tenga uno de los dos).
// La instancia de prueba es del plan Premium, con todos los módulos prendidos: lo que falta en el menú no falta por el plan.

const ADMIN = [
  '/dashboard', '/facturas', '/recibos', '/presupuestos', '/remitos', '/ventas', '/clientes', '/cuenta-corriente', '/egresos',
  '/proveedores', '/productos', '/listas-precio', '/stock', '/depositos', '/caja', '/turnos', '/cajas', '/tesoreria', '/mp-bandeja',
  '/comprobantes-pendientes', '/reportes', '/reportes/caja-medios', '/libros-iva', '/config', '/usuarios', '/logs',
]

/** Lo que sólo ve el admin (`adminOnly: true` en el Layout). */
const SOLO_ADMIN = ['/tesoreria', '/comprobantes-pendientes', '/libros-iva', '/usuarios', '/logs']

const DE_LOS_DEMAS = ADMIN.filter((r) => !SOLO_ADMIN.includes(r))

/** Los links del sidebar de cada rol, sin repetir (el logo y «Dashboard» apuntan los dos a `/dashboard`) y sin orden. */
export const MENU_POR_ROL: Record<Rol, string[]> = {
  admin: ADMIN,
  operador: DE_LOS_DEMAS,
  cajero: DE_LOS_DEMAS,
}

/** A dónde cae cada rol al entrar: la raíz redirige a `/dashboard` y el Layout lo tiene de `homeTo` para todos. */
export const INICIO_POR_ROL: Record<Rol, string> = {
  admin: '/dashboard',
  operador: '/dashboard',
  cajero: '/dashboard',
}

/** Las pantallas que el menú no ofrece al que no es admin, con el endpoint que además se las corta en el servidor (403). */
export const PROHIBIDAS_AL_QUE_NO_ES_ADMIN = [
  { ruta: '/usuarios', endpoint: '/api/usuarios' },
  { ruta: '/logs', endpoint: '/api/logs' },
  { ruta: '/tesoreria', endpoint: '/api/tesoreria' },
  { ruta: '/libros-iva', endpoint: '/api/libros-iva' },
  { ruta: '/comprobantes-pendientes', endpoint: '/api/comprobantes-pendientes' },
]
