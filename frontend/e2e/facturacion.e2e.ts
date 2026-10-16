import type { APIRequestContext, Page } from '@playwright/test'
import { esperarApi, expect, test } from 'libra-ui/e2e'
import { crearCliente, crearFactura, json, movimientosDeCaja, pesos, unico } from './datos'

// Emitir y cobrar una factura, de punta a punta y sin ARCA: el formulario de «Nueva factura», el comprobante que queda, su PDF, y el
// cobro de a partes con la caja. Con `ENV=development` y sin certificado el CAE es simulado (ver `venta-y-factura.e2e.ts`) y el emisor
// de la instancia de prueba es monotributista: el único tipo es la Factura C y no discrimina IVA (el total es cantidad × precio).

type FacturaDetalle = {
  factura: { id: number; tipo: number; total: number; cae: string | null; cliente_razon: string; items: Array<{ description: string; qty: number; unit_price: number }> }
  total_cobrado: number
  pendiente: number
  cobros: unknown[]
}

async function detalleDe(api: APIRequestContext, id: number): Promise<FacturaDetalle> {
  return json<FacturaDetalle>(await api.get(`/api/facturas/${id}`, { maxRetries: 3 }), 'GET /api/facturas/{id}')
}

test.describe('facturas', () => {
  test.use({ rol: 'operador' })

  test('se emite una Factura C desde el formulario: total, CAE, PDF y lista de comprobantes', async ({ page, api, apiDe }) => {
    const cliente = await crearCliente(await apiDe('admin'))
    const descripcion = unico('Servicio de instalación')

    await page.goto('/facturas/nueva')
    await expect(page.getByRole('button', { name: 'Emitir factura' })).toBeDisabled() // sin tipo elegido no se emite
    await page.getByRole('combobox').filter({ hasText: 'Elegir…' }).click()
    await page.getByRole('option', { name: 'Factura C' }).click()
    const selector = page.getByRole('combobox', { name: 'Cliente' })
    await selector.click()
    await selector.fill(cliente.name)
    await page.getByRole('option', { name: new RegExp(cliente.name) }).click()

    const fila = page.getByRole('row').filter({ has: page.getByRole('textbox', { name: 'Descripción o producto…' }) })
    await fila.getByRole('textbox').fill(descripcion)
    await fila.getByRole('spinbutton').nth(0).fill('3')
    await fila.getByRole('spinbutton').nth(1).fill('1500')
    // El formulario ya calcula lo que se va a emitir.
    await expect(page.getByRole('row', { name: /^TOTAL/ })).toContainText(pesos(4_500))
    await expect(page.getByRole('button', { name: 'Emitir factura' })).toBeEnabled()

    const alta = esperarApi(page, '/api/facturas', { metodo: 'POST' })
    await page.getByRole('button', { name: 'Emitir factura' }).click()
    const respuesta = await alta
    expect(respuesta.ok(), `POST /api/facturas -> ${respuesta.status()}`).toBe(true)
    const emitida = (await respuesta.json()) as { id: number }

    // Lleva al comprobante: número, receptor, ítems y el CAE.
    await expect(page).toHaveURL(new RegExp(`/facturas/${emitida.id}$`))
    await expect(page.getByRole('heading', { level: 2 })).toHaveText(/^FACTURA C 0001-\d{8}$/)
    await expect(page.getByText('Comprobante autorizado por ARCA')).toBeVisible()
    await expect(page.getByText(`Razón social: ${cliente.name}`)).toBeVisible()
    await expect(page.getByRole('row', { name: new RegExp(descripcion) })).toContainText(pesos(4_500))
    await expect(page.getByText('Pendiente de cobro')).toBeVisible()

    // Y lo guardado es lo mismo: Factura C (tipo 11) por 4.500, con CAE y sin nada cobrado todavía.
    const guardada = await detalleDe(api, emitida.id)
    expect(guardada.factura).toMatchObject({ tipo: 11, total: 4_500, cliente_razon: cliente.name })
    expect(guardada.factura.cae, 'CAE (simulado en development)').toBeTruthy()
    expect(guardada.factura.items).toEqual([{ description: descripcion, qty: 3, unit_price: 1_500, subtotal: 4_500 }])
    expect(guardada).toMatchObject({ total_cobrado: 0, pendiente: 4_500 })

    // El PDF del comprobante se baja de verdad.
    const pdf = await api.get(`/facturas/${emitida.id}/pdf`)
    expect(pdf.status()).toBe(200)
    expect(pdf.headers()['content-type']).toContain('application/pdf')
    expect((await pdf.body()).subarray(0, 4).toString()).toBe('%PDF')

    // La lista de comprobantes la trae, a nombre del cliente y sin cobrar.
    await page.goto('/facturas')
    const enLista = page.getByRole('row', { name: new RegExp(cliente.name) })
    await expect(enLista).toContainText(pesos(4_500))
    await expect(enLista).toContainText('Sin cobrar')
  })

  test('el cobro de a partes: lo pendiente baja, la caja asienta cada cobro y al completar queda cobrada', async ({ page, api, apiDe }) => {
    const admin = await apiDe('admin')
    const cliente = await crearCliente(admin)
    const factura = await crearFactura(admin, { cliente, precio: 1_500, cantidad: 3 })

    await page.goto(`/facturas/${factura.id}`)
    await expect(page.getByText('Pendiente de cobro')).toBeVisible()

    // Parcial: 1.000 de 4.500.
    await cobrar(page, factura.id, 1_000)
    await expect(page.getByText('Pago parcial')).toBeVisible()
    await expect(page.getByText(/Pendiente:/)).toContainText(pesos(3_500))
    expect(await detalleDe(api, factura.id)).toMatchObject({ total_cobrado: 1_000, pendiente: 3_500 })

    // El cobro vino con el resto sugerido: el diálogo propone lo que falta, y con eso se completa.
    await page.getByRole('button', { name: 'Registrar cobro' }).click()
    const dialogo = page.getByRole('dialog', { name: 'Registrar cobro' })
    await expect(dialogo.getByRole('spinbutton')).toHaveValue('3500')
    const resto = esperarApi(page, `/api/facturas/${factura.id}/cobrar`, { metodo: 'POST' })
    await dialogo.getByRole('button', { name: 'Confirmar cobro' }).click()
    expect((await resto).ok()).toBe(true)
    await expect(page.getByText('Cobrado completo')).toBeVisible()
    expect(await detalleDe(api, factura.id)).toMatchObject({ total_cobrado: 4_500, pendiente: 0 })

    // La caja asentó los dos cobros, atados a la factura.
    const deLaFactura = (await movimientosDeCaja(api)).filter((m) => m.concepto.includes(cliente.name))
    expect(deLaFactura.map((m) => Number(m.monto)).sort((a, b) => a - b)).toEqual([1_000, 3_500])
    for (const m of deLaFactura) expect(m.tipo).toBe('ingreso')

    // Y la lista la da por cobrada.
    await page.goto('/facturas')
    await expect(page.getByRole('row', { name: new RegExp(cliente.name) })).toContainText('Cobrada')
  })

  // 🟢 ARREGLADO en libracore v1.171.0 (ADR-058). El 2026-10-15 se midió que `POST /api/facturas/{id}/cobrar` aceptaba un cobro MAYOR que lo
  // pendiente: una factura de 4.500 con 1.000 cobrados y 3.500 pendientes aceptó un cobro de 9.999 (200), la pantalla pasaba a «Cobrado
  // completo — $ 10.999,00 (2 pagos)» y la caja asentaba un ingreso de 9.999 que nadie debía. Ahora el motor da 409 y no escribe nada.
  // (Cobrar de más en una CUENTA CORRIENTE sí es válido —queda a favor—; en una factura puntual no.)
  test('no se puede cobrar más de lo que falta de una factura', async ({ api, apiDe }) => {
    const admin = await apiDe('admin')
    const factura = await crearFactura(admin, { cliente: await crearCliente(admin), precio: 1_500, cantidad: 3 })
    const cobro = (monto: number) => api.post(`/api/facturas/${factura.id}/cobrar`, {
      data: { fecha: new Date().toLocaleDateString('en-CA', { timeZone: 'America/Argentina/Buenos_Aires' }), caja_id: 1, pagos: [{ medio_id: 'efectivo', monto, referencia: '' }] },
    })
    expect((await cobro(1_000)).ok()).toBe(true)
    const demas = await cobro(9_999)
    expect(demas.status(), 'cobrar 9.999 con 3.500 pendientes').toBeGreaterThanOrEqual(400)
    expect(demas.status()).toBeLessThan(500)
    expect(await detalleDe(api, factura.id)).toMatchObject({ total_cobrado: 1_000, pendiente: 3_500 })
  })
})

/** «Registrar cobro» de una factura, por la pantalla, con el monto que se pida (el diálogo trae lo pendiente, en efectivo y Caja Principal). */
async function cobrar(page: Page, facturaId: number, monto: number): Promise<void> {
  await page.getByRole('button', { name: 'Registrar cobro' }).click()
  const dialogo = page.getByRole('dialog', { name: 'Registrar cobro' })
  await dialogo.getByRole('spinbutton').fill(String(monto))
  const alta = esperarApi(page, `/api/facturas/${facturaId}/cobrar`, { metodo: 'POST' })
  await dialogo.getByRole('button', { name: 'Confirmar cobro' }).click()
  const respuesta = await alta
  expect(respuesta.ok(), `POST cobrar -> ${respuesta.status()}`).toBe(true)
  await expect(dialogo).toBeHidden()
}
