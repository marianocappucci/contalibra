import type { Page } from '@playwright/test'
import { expect, ponerModo, sinTextoIlegible, test } from 'libra-ui/e2e'
import { abrirTurno, cerrarTurno, crearCliente, crearFactura, crearProducto, pagarPorApi, venderPorApi } from './datos'
import { MENU_POR_ROL } from './menus'

// El modo oscuro, probado en un navegador real: todo texto visible de cada pantalla del menú del admin llega al contraste mínimo
// (WCAG AA, 4,5:1; 3:1 el texto grande). Es la pasada visual que se hizo a mano el 2026-10-02 (el nombre del producto casi
// invisible, el verde de éxito a 4,28:1), automática: un `text-[#2d2d2d]` fijo o un token sin variante oscura pone rojo el PR que lo
// introduce. `ponerModo` / `sinTextoIlegible` son de `libra-ui/e2e` (v0.152.0); el modo se guarda por navegador en `localStorage` y
// se aplica antes del primer cuadro, igual que cuando alguien lo elige con el botón sol/luna.
//
// Mide texto, no bordes, íconos ni gráficos, y no mide el texto sobre un fondo con degradé o imagen (ver `sinTextoIlegible`). Si una
// pantalla tiene algo que se ve igual en los dos modos a propósito, se exime con `ignorar: '<selector>'` y la razón escrita acá, no
// aflojando el mínimo.

// Contrastes conocidos: pantalla -> lo medido. Un defecto real se anota acá (texto sobre un color que no llega a 4,5:1; los colores no
// cambian entre claro y oscuro, así que está en los dos modos) y el spec lo deja en `fixme`; cuando el kit lo corrige, se saca.
// 🟢 Vacía desde libra-ui v0.154.0 (ADR-067): el 2026-10-15 la primera corrida encontró la insignia «FC» de `/facturas` (2,71:1), las
// del tipo de evento de `/logs` («Factura» 1,96:1, «Turno» 2,57:1, «Presupuesto» 2,13:1) y el botón «Registrar pago» de
// `/cuenta-corriente/:id` (3,77:1); el kit oscurece el fondo lo justo para llegar a 4,5:1.
const CONTRASTE_CONOCIDO: Record<string, string> = {}

/** Mide la pantalla ya cargada, salvo que su defecto esté en `CONTRASTE_CONOCIDO`. */
async function leerseEn(page: Page, clave: string): Promise<void> {
  test.fixme(clave in CONTRASTE_CONOCIDO, `contraste conocido en modo oscuro: ${CONTRASTE_CONOCIDO[clave]}`)
  await sinTextoIlegible(page)
}

/** Con los datos ya cargados: el texto de «Cargando…» no es el de la pantalla. */
async function pantallaCargada(page: Page): Promise<void> {
  await expect(page.getByRole('heading', { level: 2 }).first()).toBeVisible()
  await expect(page.getByText(/^Cargando/)).toHaveCount(0)
}

test.describe('modo oscuro: el texto se lee en cada pantalla del menú', () => {
  test.use({ rol: 'admin' })

  for (const ruta of MENU_POR_ROL.admin) {
    test(`${ruta}`, async ({ page }) => {
      await ponerModo(page, 'oscuro')
      await page.goto(ruta)
      await pantallaCargada(page)
      await leerseEn(page, ruta)
    })
  }

  test.describe('las pantallas que se arman con datos', () => {
    test('/caja, /turnos/:id y el cierre, con un turno abierto y una venta', async ({ page, api }) => {
      const producto = await crearProducto(api, { precio: 1_234 })
      const turno = await abrirTurno(api, api, 5_000)
      try {
        await venderPorApi(api, producto, { cantidad: 2 })
        await ponerModo(page, 'oscuro')
        for (const ruta of ['/caja', `/turnos/${turno}`, `/turnos/${turno}/cerrar`]) {
          await page.goto(ruta)
          await pantallaCargada(page)
          await sinTextoIlegible(page)
        }
      } finally {
        await cerrarTurno(api)
      }
    })

    test('/ventas/:id y /clientes/:id, una venta a cuenta corriente', async ({ page, api }) => {
      const cliente = await crearCliente(api)
      const producto = await crearProducto(api, { precio: 4_321 })
      const venta = await venderPorApi(api, producto, { cantidad: 3, medio: 'cuenta_corriente', cliente })
      await ponerModo(page, 'oscuro')
      for (const ruta of [`/ventas/${venta.id}`, `/clientes/${cliente.id}`]) {
        await page.goto(ruta)
        await pantallaCargada(page)
        await sinTextoIlegible(page)
      }
    })

    test('/facturas/:id', async ({ page, api }) => {
      const factura = await crearFactura(api, { cliente: await crearCliente(api), precio: 1_500, cantidad: 2 })
      await ponerModo(page, 'oscuro')
      await page.goto(`/facturas/${factura.id}`)
      await pantallaCargada(page)
      await sinTextoIlegible(page)
    })

    test('/cuenta-corriente/:id, con una deuda y un pago', async ({ page, api }) => {
      const cliente = await crearCliente(api)
      const producto = await crearProducto(api, { precio: 4_321 })
      await venderPorApi(api, producto, { cantidad: 3, medio: 'cuenta_corriente', cliente })
      await pagarPorApi(api, cliente, 5_000)
      await ponerModo(page, 'oscuro')
      await page.goto(`/cuenta-corriente/${cliente.id}`)
      await pantallaCargada(page)
      await leerseEn(page, '/cuenta-corriente/:id')
    })

    test('los formularios: nueva factura, nuevo presupuesto y nuevo remito', async ({ page }) => {
      await ponerModo(page, 'oscuro')
      for (const ruta of ['/facturas/nueva', '/presupuestos/nuevo', '/remitos/nuevo']) {
        await page.goto(ruta)
        await pantallaCargada(page)
        await sinTextoIlegible(page)
      }
    })
  })
})
