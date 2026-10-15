import { esperarApi, expect, test } from 'libra-ui/e2e'
import {
  abrirTurno, cerrarTurno, crearCliente, crearProducto, json, movimientosDeCaja, pesos, stockDe, ventaPorId, venderPorApi,
} from './datos'
import { registrarVentaPorPantalla } from './ventas'

// El camino que más plata mueve de Contalibra, de punta a punta y sin ARCA: se vende por la pantalla, se factura la venta, y se
// deshace pasando por donde obliga la ley (con la factura emitida no se anula la venta hasta tener la nota de crédito).
//
// 🔑 Cómo se evita ARCA: la instancia de prueba corre con `ENV=development` y sin certificado. Con eso `solicitar_cae()` (`libracore/
// arca_facturacion.py`) no sale a la red: pone un CAE simulado (`_dev_mock_`), y el emisor es monotributista, así que el único
// comprobante es la Factura C. La pantalla dice «la emitió ARCA» igual: es el CAE de mentira, con el flujo y el PDF de verdad.
// Los unitarios del backend evitan ARCA de la misma manera (`tests/conftest.py`: `sin_red_de_verdad` prohíbe `afip.gov.ar`/`arca.gob.ar`).

test.describe('una venta por la pantalla y su factura', () => {
  test.use({ rol: 'operador' })

  test('se registra la venta, descuenta el stock, entra a la caja y al turno, y se factura una sola vez', async ({ page, api, apiDe }) => {
    const admin = await apiDe('admin')
    const producto = await crearProducto(admin, { precio: 2_500, stock: 10 })
    const cliente = await crearCliente(admin)
    await abrirTurno(api, admin, 1_000)

    try {
      // ── La venta, por la pantalla ────────────────────────────────────────
      await page.goto('/ventas')
      const venta = await registrarVentaPorPantalla(page, { producto, cantidad: 2, cliente })
      expect(venta).toMatchObject({ total: 5_000, estado: 'cobrada', cliente_id: cliente.id })

      // Al registrar, la pantalla lleva al detalle de la venta nueva: lo que se vendió, a quién y cómo se cobró.
      await expect(page).toHaveURL(new RegExp(`/ventas/${venta.id}$`))
      await expect(page.getByRole('heading', { name: `Venta ${venta.numero} Cobrada` })).toBeVisible()
      await expect(page.getByText(`Cliente: ${cliente.name}`)).toBeVisible()
      await expect(page.getByRole('row', { name: new RegExp(producto.nombre) })).toContainText(pesos(5_000))
      await expect(page.getByText('Total cobrado').locator('xpath=..')).toContainText(pesos(5_000))
      // …y lo que quedó en el servidor: el stock bajó, la plata entró a la caja y la venta cuenta en el arqueo del turno.
      expect(await stockDe(admin, producto)).toBe(8)
      const ingreso = (await movimientosDeCaja(admin)).find((m) => m.concepto.startsWith(`Venta ${venta.numero}`))
      expect(ingreso, 'el movimiento de caja de la venta').toMatchObject({ tipo: 'ingreso', monto: 5_000 })
      const resumen = await json<{ resumen: { ventas: Array<{ numero: string }>; efectivo_ventas: number } }>(
        await api.get('/api/turnos/actual'), 'GET /api/turnos/actual')
      expect(resumen.resumen.ventas.map((v) => v.numero)).toContain(venta.numero)
      expect(Number(resumen.resumen.efectivo_ventas)).toBe(5_000)

      // ── Se factura desde el detalle ──────────────────────────────────────
      const facturar = esperarApi(page, `/api/ventas/${venta.id}/facturar`, { metodo: 'POST' })
      await page.getByRole('button', { name: 'Generar factura' }).click()
      expect((await facturar).ok()).toBe(true)

      const enlace = page.getByRole('link', { name: /^FACTURA C 0001-\d{8}$/ })
      await expect(enlace).toBeVisible()
      const facturada = await ventaPorId(api, venta.id)
      expect(facturada.factura_id).not.toBeNull()
      expect(facturada.factura_cae, 'la factura tiene CAE (simulado en development)').toBeTruthy()
      await expect(enlace).toHaveText(facturada.factura_display!)

      // La factura es lo que se vendió: Factura C (tipo 11) por 5.000, a nombre del cliente, sin IVA discriminado.
      const { factura } = await json<{ factura: { tipo: number; total: number; iva_amount: number; cliente_razon: string; cae: string } }>(
        await api.get(`/api/facturas/${facturada.factura_id}`), 'GET /api/facturas/{id}')
      expect(factura).toMatchObject({ tipo: 11, total: 5_000, iva_amount: 0, cliente_razon: cliente.name })

      // Y facturar de nuevo no emite una segunda: devuelve la misma.
      const otra = await json<{ venta: { factura_id: number } }>(
        await api.post(`/api/ventas/${venta.id}/facturar`, { data: {} }), 'POST /api/ventas/{id}/facturar (repetido)')
      expect(otra.venta.factura_id).toBe(facturada.factura_id)

      // El comprobante se baja como PDF de verdad.
      const pdf = await api.get(`/facturas/${facturada.factura_id}/pdf`)
      expect(pdf.status()).toBe(200)
      expect(pdf.headers()['content-type']).toContain('application/pdf')
      expect((await pdf.body()).subarray(0, 4).toString()).toBe('%PDF')

      // La lista de ventas muestra la venta con sus datos y la da por facturada (la pestaña «Facturadas» la incluye).
      await page.goto('/ventas')
      const fila = page.getByRole('listitem').filter({ hasText: venta.numero })
      await expect(fila).toContainText(cliente.name)
      await expect(fila).toContainText(pesos(5_000))
      await expect(fila).not.toContainText('Sin facturar')
      await page.getByRole('tab', { name: 'Facturadas' }).click()
      await expect(fila).toBeVisible()
      await page.getByRole('tab', { name: 'Sin facturar' }).click()
      await expect(fila).toHaveCount(0)
    } finally {
      await cerrarTurno(api)
    }
  })
})

test.describe('deshacer una venta facturada', () => {
  test.use({ rol: 'admin' })

  test('con la factura emitida no se anula hasta emitir la nota de crédito; después vuelve el stock y la caja lo registra', async ({ page, api, apiDe }) => {
    const operador = await apiDe('operador')
    const producto = await crearProducto(api, { precio: 3_000, stock: 10 })
    const cliente = await crearCliente(api)
    const venta = await venderPorApi(api, producto, { cantidad: 2, cliente })
    expect(await stockDe(api, producto)).toBe(8)
    await json(await api.post(`/api/ventas/${venta.id}/facturar`, { data: {} }), 'POST /api/ventas/{id}/facturar')

    // Anular es del admin: el operador no puede, ni siquiera antes de tocar la factura.
    expect((await operador.post(`/api/ventas/${venta.id}/anular`, { data: { motivo: 'e2e' } })).status()).toBe(403)
    // Y con la factura vigente ni el admin: el servidor pide la nota de crédito primero (409) y la venta sigue cobrada.
    const rechazo = await api.post(`/api/ventas/${venta.id}/anular`, { data: { motivo: 'e2e' } })
    expect(rechazo.status()).toBe(409)
    expect(await rechazo.text()).toContain('nota de crédito')
    expect(await stockDe(api, producto)).toBe(8)

    // La pantalla lo explica y ofrece la nota, no la anulación directa.
    await page.goto(`/ventas/${venta.id}`)
    await expect(page.getByText(/Para anular la venta hay que emitir antes la nota de crédito/)).toBeVisible()
    await page.getByRole('button', { name: 'Emitir nota de crédito' }).click()
    const dialogo = page.getByRole('dialog', { name: 'Emitir nota de crédito' })
    await expect(dialogo).toContainText(pesos(6_000))
    const nota = esperarApi(page, /\/api\/facturas\/\d+\/nota-credito$/, { metodo: 'POST' })
    await dialogo.getByRole('button', { name: 'Emitir nota' }).click()
    expect((await nota).ok()).toBe(true)
    await expect(page.getByText(/La nota de crédito NOTA CREDITO C 0001-\d{8} está emitida: ya podés anular la venta/)).toBeVisible()

    // Ahora sí: se anula, con la confirmación de la pantalla.
    await page.getByRole('button', { name: 'Anular venta' }).click()
    const confirmar = page.getByRole('alertdialog', { name: '¿Anular esta venta?' })
    await expect(confirmar).toContainText('Se repondrá el stock')
    const anulacion = esperarApi(page, `/api/ventas/${venta.id}/anular`, { metodo: 'POST' })
    await confirmar.getByRole('button', { name: 'Anular', exact: true }).click()
    expect((await anulacion).ok()).toBe(true)
    await expect(page.getByRole('heading', { name: new RegExp(`Venta ${venta.numero} Anulada`) })).toBeVisible()

    // El stock vuelve y la caja asienta el egreso que compensa el ingreso (no borra el original: queda el rastro).
    expect(await stockDe(api, producto)).toBe(10)
    const movimientos = (await movimientosDeCaja(api)).filter((m) => m.concepto.includes(venta.numero))
    expect(movimientos.map((m) => m.tipo).sort()).toEqual(['egreso', 'ingreso'])
    for (const m of movimientos) expect(Number(m.monto)).toBe(6_000)
  })
})
