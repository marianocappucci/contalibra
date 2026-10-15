import type { Page } from '@playwright/test'
import { esperarApi, expect, test } from 'libra-ui/e2e'
import {
  cerrarTurno, crearProducto, liberarCaja, movimientosDeCaja, pesos, turnoPorId, unico, venderPorApi,
} from './datos'

// El arqueo de la caja de punta a punta, como lo hace un cajero: abre su turno con un fondo, vende (en efectivo y con tarjeta),
// mueve la caja a mano, y al cerrar cuenta el efectivo. Lo que ningún unitario ve junto: que el «efectivo esperado» de la pantalla de
// cierre sea el fondo más SÓLO los cobros en efectivo (la tarjeta no está en el cajón, y un ingreso o egreso manual de la caja
// tampoco entra al arqueo del turno), que la diferencia se vea al tipear el conteo, y que lo que queda guardado sea lo mismo que se vio.
//
// La instancia tiene UNA caja y el turno es por usuario: cada test libera la caja antes (el admin cierra los abiertos) y deja la suya
// cerrada al terminar, aunque falle.
test.describe('el turno de un cajero', () => {
  test.use({ rol: 'cajero' })

  test('abre con un fondo, vende en efectivo y con tarjeta, mueve la caja y cierra con una diferencia', async ({ page, api, apiDe }) => {
    const admin = await apiDe('admin')
    const producto = await crearProducto(admin, { precio: 2_000 })
    const ingreso = unico('Aporte e2e')
    const egreso = unico('Gasto e2e')
    await liberarCaja(admin)

    try {
      // ── Abre el turno por la pantalla ────────────────────────────────────
      await page.goto('/turnos')
      await expect(page.getByRole('heading', { name: 'Turnos de caja' })).toBeVisible()
      await expect(page.getByText('Turno abierto', { exact: true })).toHaveCount(0)
      await page.getByRole('button', { name: 'Abrir turno' }).click()
      const dialogo = page.getByRole('dialog', { name: 'Abrir turno' })
      await dialogo.getByRole('spinbutton', { name: 'Fondo inicial' }).fill('5000')
      const apertura = esperarApi(page, '/api/turnos/abrir', { metodo: 'POST' })
      await dialogo.getByRole('button', { name: 'Abrir turno ahora' }).click()
      expect((await apertura).status()).toBe(200)

      // Al abrir, la pantalla lleva al detalle del turno nuevo, con el fondo que se escribió.
      const { turno } = await (await api.get('/api/turnos/actual')).json() as { turno: { id: number; monto_inicial: number } }
      expect(Number(turno.monto_inicial)).toBe(5_000)
      await expect(page).toHaveURL(new RegExp(`/turnos/${turno.id}$`))
      await expect(page.getByRole('heading', { name: `Turno #${turno.id} Abierto` })).toBeVisible()
      await expect(page.locator('p', { hasText: /^Fondo inicial:/ })).toContainText(pesos(5_000))

      // ── Vende: 2 × 2.000 en efectivo y 1 × 2.000 con tarjeta ─────────────
      await venderPorApi(api, producto, { cantidad: 2, medio: 'efectivo' })
      await venderPorApi(api, producto, { cantidad: 1, medio: 'tarjeta_debito' })

      // ── Mueve la caja a mano, por la pantalla de Caja ────────────────────
      await page.goto('/caja')
      await nuevoMovimiento(page, { tipo: 'Ingreso', concepto: ingreso, monto: '3000' })
      await nuevoMovimiento(page, { tipo: 'Egreso', concepto: egreso, monto: '1200' })
      await expect(page.getByRole('row', { name: new RegExp(ingreso) })).toContainText(pesos(3_000))
      await expect(page.getByRole('row', { name: new RegExp(egreso) })).toContainText(pesos(1_200))
      const movimientos = await movimientosDeCaja(api)
      expect(movimientos.find((m) => m.concepto === ingreso)).toMatchObject({ tipo: 'ingreso', monto: 3_000, anulado: 0 })
      expect(movimientos.find((m) => m.concepto === egreso)).toMatchObject({ tipo: 'egreso', monto: 1_200, anulado: 0 })

      // ── La pantalla de cierre arma el arqueo: 5.000 de fondo + 4.000 en efectivo ──
      await page.goto(`/turnos/${turno.id}/cerrar`)
      await expect(page.getByText('Ventas realizadas: 2')).toBeVisible()
      await expect(page.getByText('Total recaudado').locator('xpath=..')).toContainText(pesos(6_000))
      await expect(page.getByText('Efectivo esperado en caja').locator('xpath=..')).toContainText(pesos(9_000))
      // Sin tocar el conteo no hay diferencia; con 150 de menos, se ve.
      const contado = page.getByRole('spinbutton', { name: 'Efectivo contado en caja' })
      await expect(contado).toHaveValue('9000')
      await expect(page.getByText('Diferencia:', { exact: true }).locator('xpath=..')).toContainText('OK')
      await contado.fill('8850')
      await expect(page.getByText('Diferencia:', { exact: true }).locator('xpath=..')).toContainText(pesos(-150))
      await page.getByRole('textbox', { name: 'Notas de cierre' }).fill('Faltaron 150 de vuelto')
      const cierre = esperarApi(page, `/api/turnos/${turno.id}/cerrar`, { metodo: 'POST' })
      await page.getByRole('button', { name: 'Confirmar cierre de turno' }).click()
      expect((await cierre).status()).toBe(200)

      // ── Lo guardado es lo que se vio ─────────────────────────────────────
      const cerrado = await turnoPorId(api, turno.id)
      expect(cerrado).toMatchObject({ estado: 'cerrado' })
      expect(Number(cerrado.monto_esperado_cierre)).toBe(9_000)
      expect(Number(cerrado.monto_declarado_cierre)).toBe(8_850)
      await page.goto('/turnos')
      const fila = page.getByRole('row', { name: new RegExp(`^${turno.id} `) })
      await expect(fila).toContainText('Cerrado')
      await expect(fila).toContainText(pesos(9_000))
      await expect(fila).toContainText(pesos(8_850))
      await expect(fila).toContainText(pesos(-150))
      await expect(page.getByText('Turno abierto', { exact: true })).toHaveCount(0)
    } finally {
      await cerrarTurno(api)
    }
  })

  test('abrir con un turno abierto devuelve ese mismo turno, y el cajero no ve el de otro', async ({ page, api, apiDe }) => {
    const admin = await apiDe('admin')
    const operador = await apiDe('operador')
    await liberarCaja(admin)
    try {
      const del_operador = await (await operador.post('/api/turnos/abrir', { data: { monto_inicial: 100, notas: 'e2e' } })).json() as { id: number }
      const primero = await (await api.post('/api/turnos/abrir', { data: { monto_inicial: 200, notas: 'e2e' } })).json() as { id: number }

      // Un turno es por usuario: abrir con uno abierto devuelve ESE turno (idempotente, el servidor no abre un segundo ni cambia el fondo).
      const repetido = await api.post('/api/turnos/abrir', { data: { monto_inicial: 300, notas: 'e2e' } })
      expect(repetido.status()).toBe(200)
      expect(await repetido.json()).toMatchObject({ id: primero.id, monto_inicial: 200 })

      // El cajero sólo ve los suyos; el admin, los de todos.
      const suyos = (await (await api.get('/api/turnos')).json() as { turnos: Array<{ id: number }> }).turnos.map((t) => t.id)
      expect(suyos).not.toContain(del_operador.id)
      const todos = (await (await admin.get('/api/turnos')).json() as { turnos: Array<{ id: number }> }).turnos.map((t) => t.id)
      expect(todos).toEqual(expect.arrayContaining([...suyos, del_operador.id]))

      // El detalle del turno de otro lo corta el servidor, y la pantalla no muestra su fondo.
      expect((await api.get(`/api/turnos/${del_operador.id}`)).status()).toBe(403)
      await page.goto('/turnos')
      await expect(page.getByRole('heading', { name: 'Turnos de caja' })).toBeVisible()
      await expect(page.getByText('Mis turnos')).toBeVisible()
      await expect(page.getByRole('table').getByRole('link', { name: 'Ver detalle' })).toHaveCount(suyos.length)
      await expect(page.getByRole('row', { name: new RegExp(`^${del_operador.id} `) })).toHaveCount(0)
    } finally {
      await cerrarTurno(api)
      await cerrarTurno(operador)
    }
  })
})

/** El diálogo «Nuevo movimiento de caja» de la pantalla de Caja. */
async function nuevoMovimiento(
  page: Page,
  { tipo, concepto, monto }: { tipo: 'Ingreso' | 'Egreso'; concepto: string; monto: string },
): Promise<void> {
  await page.getByRole('button', { name: 'Nuevo movimiento' }).click()
  const dialogo = page.getByRole('dialog', { name: 'Nuevo movimiento de caja' })
  await dialogo.getByRole('combobox', { name: 'Tipo' }).click()
  await page.getByRole('option', { name: tipo, exact: true }).click()
  await dialogo.getByRole('textbox', { name: 'Concepto' }).fill(concepto)
  await dialogo.getByRole('spinbutton', { name: 'Monto' }).fill(monto)
  const alta = esperarApi(page, '/api/caja', { metodo: 'POST' })
  await dialogo.getByRole('button', { name: 'Guardar movimiento' }).click()
  expect((await alta).ok()).toBe(true)
  await expect(dialogo).toBeHidden()
}

