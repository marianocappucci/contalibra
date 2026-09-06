import { expect, test } from '@playwright/test'

// Lo único que un unitario no puede ver: que la SPA construida, servida por la
// app real, deje entrar y muestre una pantalla de dominio. Si el bundle quedó
// viejo, si el gate de Términos tapa todo, si el login devuelve un HTML por
// catch-all en vez de JSON, esto se pone rojo y los 200 unitarios no.
test('entra por /login y llega al Dashboard', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Contalibra' })).toBeVisible()

  await page.getByLabel('Usuario').fill(process.env.SMOKE_USER ?? 'admin')
  await page.getByLabel('Contraseña').fill(process.env.SMOKE_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Ingresar' }).click()

  await expect(page).toHaveURL(/\/dashboard/)
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
})

test('una credencial mala no entra (control)', async ({ page }) => {
  // Sin esto el test de arriba podría pasar con un login que acepte cualquier
  // cosa; el rechazo tiene que verse en la pantalla, no sólo en la API.
  await page.goto('/login')
  await page.getByLabel('Usuario').fill('admin')
  await page.getByLabel('Contraseña').fill('esta-no-es')
  await page.getByRole('button', { name: 'Ingresar' }).click()
  await expect(page).toHaveURL(/\/login/)
  await expect(page.getByText(/incorrect/i)).toBeVisible()
})
