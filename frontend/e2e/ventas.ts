import type { Page } from '@playwright/test'
import { esperarApi, expect } from 'libra-ui/e2e'
import type { Cliente, Producto, Venta } from './datos'

/** «Nueva venta» de `/ventas` por la pantalla, como un operador: cliente (opcional), el producto buscado por nombre, la cantidad y el
 *  medio de pago (el importe es el total). Devuelve la venta que registró el servidor. Hay que estar en `/ventas`. */
export async function registrarVentaPorPantalla(
  page: Page,
  { producto, cantidad, cliente, medio = 'Efectivo' }: { producto: Producto; cantidad: number; cliente?: Cliente; medio?: string },
): Promise<Venta> {
  await page.getByRole('button', { name: 'Nueva venta' }).click()
  const dialogo = page.getByRole('dialog', { name: 'Nueva venta' })

  if (cliente) {
    // El selector buscable: al abrirlo, el mismo campo filtra por lo que se escribe.
    const selector = dialogo.getByRole('combobox', { name: 'Cliente' })
    await selector.click()
    await selector.fill(cliente.name)
    await page.getByRole('option', { name: new RegExp(cliente.name) }).click()
  }

  // El producto se busca por nombre en «Ítem 1»; al elegirlo trae su precio.
  await dialogo.getByRole('textbox', { name: 'Ítem 1' }).fill(producto.nombre)
  await page.getByRole('button', { name: new RegExp(`^${producto.nombre} — `) }).click()
  await expect(dialogo.getByRole('spinbutton', { name: 'Precio 1' })).toHaveValue(String(producto.precio))
  await dialogo.getByRole('spinbutton', { name: 'Cantidad 1' }).fill(String(cantidad))

  if (medio !== 'Efectivo') {
    await dialogo.getByRole('combobox', { name: 'Medio de pago' }).click()
    await page.getByRole('option', { name: medio, exact: true }).click()
  }
  // Con un solo medio de pago el importe sigue al total: se espera a que lo alcance antes de registrar.
  await expect(dialogo.getByRole('spinbutton', { name: 'Importe' })).toHaveValue(String(producto.precio * cantidad))

  const alta = esperarApi(page, '/api/ventas', { metodo: 'POST' })
  await dialogo.getByRole('button', { name: 'Registrar venta' }).click()
  const respuesta = await alta
  expect(respuesta.ok(), `POST /api/ventas -> ${respuesta.status()}`).toBe(true)
  const venta = (await respuesta.json()) as Venta
  await expect(dialogo).toBeHidden()
  return venta
}
