import type { Page } from '@playwright/test'
import { descartarAvisoDeProximaVersion, esperarApi, expect, test } from 'libra-ui/e2e'
import {
  crearCliente, crearProducto, cuentaCorrienteDe, hoy, json, pagarPorApi, pesos, stockDe, venderPorApi,
} from './datos'
import { registrarVentaPorPantalla } from './ventas'

// La cuenta corriente de un cliente de punta a punta: se le vende «a cuenta» por la pantalla (el cargo), se le cobra de a partes (el
// abono y su recibo de cobranza), se le cobra de más (queda a favor) y el admin deshace un cobro. Lo que ningún unitario ve junto: que
// el saldo que muestra la pantalla —con su «Debe» / «A favor»— sea el mismo que calcula el servidor del libro de la cuenta, y que cada
// cobro deje su recibo y se pueda anular sólo por quien puede (el admin).
//
// Convención del servidor: `saldo` positivo es lo que el cliente DEBE; negativo, lo que tiene A FAVOR.

test.describe('la cuenta corriente de un cliente', () => {
  test.use({ rol: 'operador' })

  test('una venta a cuenta es un cargo; cada cobro baja el saldo, deja su recibo, y cobrar de más deja saldo a favor', async ({ page, api, apiDe }) => {
    const admin = await apiDe('admin')
    const producto = await crearProducto(admin, { precio: 4_000, stock: 10 })
    const cliente = await crearCliente(admin)

    // ── El cargo: una venta con medio «Cuenta corriente», por la pantalla ──
    await page.goto('/ventas')
    const venta = await registrarVentaPorPantalla(page, { producto, cantidad: 3, cliente, medio: 'Cuenta corriente' })
    expect(venta).toMatchObject({ total: 12_000, cliente_id: cliente.id })
    expect(await stockDe(admin, producto), 'vender a cuenta también descuenta stock').toBe(7)
    expect(await cuentaCorrienteDe(api, cliente)).toMatchObject({ saldo: 12_000 })

    // La cuenta corriente lo muestra: en la lista de deudores y en su propia pantalla.
    await page.goto('/cuenta-corriente')
    const fila = page.getByRole('row', { name: new RegExp(cliente.name) })
    await expect(fila).toContainText(pesos(12_000))
    await fila.getByRole('link', { name: 'Ver cuenta corriente' }).click()
    await expect(page).toHaveURL(new RegExp(`/cuenta-corriente/${cliente.id}$`))
    await expect(page.getByRole('heading', { level: 2 })).toHaveText(new RegExp(`${cliente.name}\\s*Debe\\s*`))
    await expect(page.getByRole('heading', { level: 2 })).toContainText(pesos(12_000))
    await expect(page.getByText('Saldo actual').locator('xpath=..')).toContainText(pesos(12_000))
    await expect(page.getByRole('row', { name: /Cargo/ })).toContainText(pesos(12_000))

    // ── Un cobro parcial por la pantalla ─────────────────────────────────
    await cobrar(page, cliente.id, 5_000)
    expect((await cuentaCorrienteDe(api, cliente)).saldo).toBe(7_000)
    await expect(page.getByRole('heading', { level: 2 })).toContainText(pesos(7_000))
    await expect(page.getByText('Total abonado').locator('xpath=..')).toContainText(pesos(5_000))
    await expect(page.getByRole('row', { name: /Abono/ })).toContainText(pesos(5_000))

    // El cobro dejó su recibo de cobranza, por lo cobrado y a nombre del cliente.
    const recibos = await json<{ recibos: Array<{ cliente_id: number; total: number; origen_tipo: string; anulado: boolean }> }>(
      await api.get('/api/recibos', { params: { cliente_id: cliente.id } }), 'GET /api/recibos')
    const deEste = recibos.recibos.filter((r) => r.cliente_id === cliente.id)
    expect(deEste).toHaveLength(1)
    expect(deEste[0]).toMatchObject({ total: 5_000, origen_tipo: 'cc_pago', anulado: false })

    // ── Cobrar de más: el saldo pasa a ser a favor del cliente ──────────
    await pagarPorApi(api, cliente, 8_000, 'Pago e2e de más')
    await page.reload()
    await expect(page.getByRole('heading', { level: 2 })).toHaveText(new RegExp(`${cliente.name}\\s*A favor\\s*`))
    await expect(page.getByRole('heading', { level: 2 })).toContainText(pesos(1_000))
    expect((await cuentaCorrienteDe(api, cliente)).saldo).toBe(-1_000)
  })

  test('el operador no puede borrar un cobro; el admin sí, y la deuda vuelve y el recibo queda anulado', async ({ page, api, apiDe }) => {
    const admin = await apiDe('admin')
    const producto = await crearProducto(admin, { precio: 2_000, stock: 10 })
    const cliente = await crearCliente(admin)
    await venderPorApi(admin, producto, { cantidad: 2, medio: 'cuenta_corriente', cliente })
    const { recibo_id } = await pagarPorApi(admin, cliente, 1_500, 'Cobro que se deshace')
    const cc = await cuentaCorrienteDe(admin, cliente)
    expect(cc.saldo).toBe(2_500)
    const pagoId = cc.movimientos.find((m) => m.tipo === 'credito')!.cc_pago_id!

    // El operador ve la cuenta pero no tiene el botón, y el servidor tampoco se lo deja.
    await page.goto(`/cuenta-corriente/${cliente.id}`)
    await expect(page.getByRole('row', { name: /Abono/ })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Eliminar pago' })).toHaveCount(0)
    const prohibido = await api.delete(`/api/cuenta-corriente/pagos/${pagoId}`)
    expect(prohibido.status()).toBe(403)
    expect((await cuentaCorrienteDe(admin, cliente)).saldo).toBe(2_500)

    // El admin lo borra por la pantalla, con su confirmación.
    const pantallaAdmin = await page.context().browser()!.newContext({ storageState: await admin.storageState() })
    const paginaAdmin = await pantallaAdmin.newPage()
    try {
      await paginaAdmin.goto(`/cuenta-corriente/${cliente.id}`)
      await expect(paginaAdmin.getByRole('row', { name: /Abono/ })).toContainText(pesos(1_500))
      // Un contexto nuevo no pasa por `entrarComo`: el aviso de la próxima versión de los Términos (libra-ui v0.153.0) aparece.
      await descartarAvisoDeProximaVersion(paginaAdmin)
      await paginaAdmin.getByRole('button', { name: 'Eliminar pago' }).click()
      const baja = esperarApi(paginaAdmin, `/api/cuenta-corriente/pagos/${pagoId}`, { metodo: 'DELETE' })
      await paginaAdmin.getByRole('alertdialog').getByRole('button', { name: /Eliminar|Confirmar|Sí/ }).last().click()
      expect((await baja).ok()).toBe(true)
      await expect(paginaAdmin.getByRole('heading', { level: 2 })).toContainText(pesos(4_000))
    } finally {
      await pantallaAdmin.close()
    }

    // La deuda volvió a lo que era y el recibo del cobro quedó anulado (no borrado: queda el rastro).
    expect((await cuentaCorrienteDe(admin, cliente)).saldo).toBe(4_000)
    const recibos = await json<{ recibos: Array<{ id: number; anulado: boolean }> }>(await admin.get('/api/recibos'), 'GET /api/recibos')
    expect(recibos.recibos.find((r) => r.id === recibo_id)).toMatchObject({ anulado: true })
  })

  // 🔴 DEFECTO REAL (2026-10-15, medido en esta rama): `POST /api/ventas` acepta un pago en `cuenta_corriente` SIN cliente (200, venta
  // V-0000N con `cliente_id: null`). La deuda queda a nombre de nadie: no aparece en ninguna cuenta corriente y no se puede cobrar. El
  // motor ya trae la regla (`OpcionesVentas.exigir_cliente_para_fiar`: «una deuda que no es de nadie no se puede cobrar», 422 antes de
  // escribir nada) y VentaLibra la prende; `app/web/api/ventas.py` de Contalibra arma `OpcionesVentas` sin ella. Lo decide el humano
  // (cambia el comportamiento de hoy); mientras tanto queda en `fixme`.
  test('una venta a cuenta corriente sin cliente se rechaza', async ({ api, apiDe }) => {
    test.fixme(true, 'defecto de la app: el servidor acepta fiar sin cliente (falta `exigir_cliente_para_fiar` en OpcionesVentas)')
    const admin = await apiDe('admin')
    const producto = await crearProducto(admin, { precio: 1_000, stock: 5 })
    const respuesta = await api.post('/api/ventas', {
      data: {
        fecha: hoy(), cliente_id: null,
        items: [{ nombre: producto.nombre, qty: 1, precio: 1_000, producto_id: producto.id }],
        pagos: [{ medio: 'cuenta_corriente', monto: 1_000 }],
      },
    })
    expect(respuesta.status()).toBe(422)
    expect(await stockDe(admin, producto), 'una venta rechazada no descuenta stock').toBe(5)
  })
})

/** «Registrar pago» de la cuenta de un cliente, por la pantalla (el diálogo viene con el saldo completo; se cambia el monto). */
async function cobrar(page: Page, clienteId: number, monto: number): Promise<void> {
  await page.getByRole('button', { name: 'Registrar pago' }).click()
  const dialogo = page.getByRole('dialog', { name: /^Registrar pago — / })
  await dialogo.getByRole('spinbutton').fill(String(monto))
  const alta = esperarApi(page, `/api/cuenta-corriente/${clienteId}/pagar`, { metodo: 'POST' })
  await dialogo.getByRole('button', { name: 'Registrar pago' }).click()
  const respuesta = await alta
  expect(respuesta.ok(), `POST pagar -> ${respuesta.status()}`).toBe(true)
}
