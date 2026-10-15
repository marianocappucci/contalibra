import type { Page } from '@playwright/test'
import { expect, sinDesborde, test } from 'libra-ui/e2e'
import {
  abrirTurno, cerrarTurno, crearCliente, crearFactura, crearProducto, pagarPorApi, venderPorApi,
} from './datos'
import { MENU_POR_ROL } from './menus'

// Lo que sólo ve un navegador real, y que ya rompió: las pantallas que se desbordan a lo ancho en un celular (390 px) y no en el
// monitor (1280 px). Las rutas salen de la tabla del menú del admin (`menus.ts`), que el spec de roles verifica contra el sidebar
// real: una pantalla nueva entra acá en cuanto entra al menú. Los detalles (una venta, una factura, la ficha de un cliente, su cuenta
// corriente, un turno) no están en el menú: se siembran por la API y se abren por su link.

/** Con los datos ya cargados: un desborde que viene de una fila larga no existe mientras dice «Cargando…». */
async function pantallaCargada(page: Page): Promise<void> {
  await expect(page.getByRole('heading', { level: 2 }).first()).toBeVisible()
  await expect(page.getByText(/^Cargando/)).toHaveCount(0)
}

// 🔴 DEFECTOS REALES que este spec encontró el 2026-10-15 (primera corrida, `develop` @ 23f04dc, libra-ui v0.152.1): ocho pantallas se
// desbordan a 390 px —el documento mide más que la ventana y el celular scrollea de costado— y a 1280 px están bien. Son pantallas del
// kit (`libra-ui/Facturas`, `libra-ui/comercio/Logs`...) y el arreglo va ahí, no en Contalibra; mientras tanto el ancho de escritorio
// se mide igual y el de celular queda en `fixme` con lo medido. Cuando una se arregla, se saca de esta tabla y el spec la cuida.
// El elemento es el primero que se pasa del borde, tal como lo informa `sinDesborde`.
const DESBORDE_A_390: Record<string, string> = {
  '/facturas': 'el documento mide 579 px: la fila de pestañas de estado (`div.inline-flex.h-9.w-fit`, un TabsList) no se parte ni scrollea',
  '/mp-bandeja': 'el documento mide 670 px: el TabsList «Cobros / ...» (`button#...-trigger-cobros`) no se parte ni scrollea',
  '/logs': 'el documento mide 394 px: el TabsList «Actividad / Accesos» y el título se pasan 4 px',
  '/libros-iva': 'el documento mide 415 px: `table.w-full.text-sm` sin contenedor `overflow-x-auto`',
  '/facturas/nueva': 'el documento mide 405 px: una fila `flex flex-wrap items-end` con un campo `flex-1` que no baja de ancho',
  '/presupuestos/nuevo': 'el documento mide 405 px: la misma fila `flex flex-wrap items-end` que Nueva factura',
  '/facturas/:id': 'el documento mide 429 px: `table.w-full.text-sm` de los ítems, sin `overflow-x-auto`',
  '/turnos/:id': 'el documento mide 487 px: `table.w-full.text-sm` de las ventas del turno, sin `overflow-x-auto`',
}

/** Abre la ruta, espera los datos y mide los dos anchos. `clave` es la de `DESBORDE_A_390` (por defecto, la propia ruta). */
async function abrir(page: Page, ruta: string, clave = ruta): Promise<void> {
  await page.goto(ruta)
  await pantallaCargada(page)
  await sinDesborde(page, [1280])
  test.fixme(clave in DESBORDE_A_390, `desborde conocido a 390 px: ${DESBORDE_A_390[clave]}`)
  await sinDesborde(page, [390])
}

test.describe('sin desborde a 390 y a 1280 px', () => {
  test.use({ rol: 'admin' })

  for (const ruta of MENU_POR_ROL.admin) {
    test(`${ruta}`, async ({ page }) => {
      await abrir(page, ruta)
    })
  }

  for (const ruta of ['/facturas/nueva', '/remitos/nuevo', '/presupuestos/nuevo', '/mi-cuenta']) {
    test(`${ruta}`, async ({ page }) => {
      await abrir(page, ruta)
    })
  }

  // Los detalles: cada uno con SU test, para que el que se desborda no tape a los que no.
  test.describe('los detalles de lo que se opera', () => {
    test('/ventas/:id, una venta a cuenta corriente', async ({ page, api }) => {
      const cliente = await crearCliente(api)
      const producto = await crearProducto(api, { precio: 4_321 })
      const venta = await venderPorApi(api, producto, { cantidad: 3, medio: 'cuenta_corriente', cliente })
      await abrir(page, `/ventas/${venta.id}`)
    })

    test('/facturas/:id', async ({ page, api }) => {
      const factura = await crearFactura(api, { cliente: await crearCliente(api), precio: 1_500, cantidad: 2 })
      await abrir(page, `/facturas/${factura.id}`, '/facturas/:id')
    })

    test('/clientes/:id', async ({ page, api }) => {
      await abrir(page, `/clientes/${(await crearCliente(api)).id}`)
    })

    test('/cuenta-corriente/:id, con una deuda y un pago', async ({ page, api }) => {
      const cliente = await crearCliente(api)
      const producto = await crearProducto(api, { precio: 4_321 })
      await venderPorApi(api, producto, { cantidad: 3, medio: 'cuenta_corriente', cliente })
      await pagarPorApi(api, cliente, 5_000)
      await abrir(page, `/cuenta-corriente/${cliente.id}`)
    })
  })

  test.describe('con un turno abierto y una venta en efectivo', () => {
    const rutas = [
      { nombre: '/caja', ruta: () => '/caja' },
      { nombre: '/turnos', ruta: () => '/turnos' },
      { nombre: '/turnos/:id', ruta: (turno: number) => `/turnos/${turno}` },
      { nombre: '/turnos/:id/cerrar', ruta: (turno: number) => `/turnos/${turno}/cerrar` },
    ]
    for (const { nombre, ruta } of rutas) {
      test(nombre, async ({ page, api }) => {
        const producto = await crearProducto(api, { precio: 1_234 })
        const turno = await abrirTurno(api, api, 5_000)
        try {
          await venderPorApi(api, producto, { cantidad: 2 })
          await abrir(page, ruta(turno), nombre)
        } finally {
          await cerrarTurno(api)
        }
      })
    }
  })
})
