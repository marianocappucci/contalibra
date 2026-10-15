import { expect, test as base, type Page } from '@playwright/test'
import { aceptarTerminos, rutaAuth, SIDEBAR, tildarCaptcha, type Credenciales } from 'libra-ui/e2e'

// 🔴 El `entrarComo` y el `prepararSesiones` de `libra-ui/e2e` le preguntan los Términos a `GET /terminos` (la ruta de VentaLibra). En
// Contalibra el router de Términos va bajo `/api/terminos` (`build_terminos_router(prefix=...)` en `app/web/app.py`, y
// `terminosPath` en `context/AuthContext.tsx`): `/terminos` cae en el fallback de la SPA, que contesta el `index.html` con 200, y el
// helper del kit se rompe con `Unexpected token '<'`. `aceptarTerminos` ya acepta `{ ruta }`; lo que le falta al kit es que
// `entrarComo` y `prepararSesiones` se la pasen. Hasta que lo tengan, estas dos son las del kit con la ruta de acá.
const RUTA_DE_TERMINOS = '/api/terminos'

/** `/login` completo (usuario, contraseña, captcha), los Términos si están pendientes y espera el sidebar. */
export async function entrarComo(page: Page, { usuario, clave }: Credenciales): Promise<void> {
  await page.goto('/login')
  await expect(page.getByRole('button', { name: 'Ingresar' })).toBeVisible()
  await page.locator('#username').fill(usuario)
  await page.locator('#password').fill(clave)
  await tildarCaptcha(page)
  await page.getByRole('button', { name: 'Ingresar' }).click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'))
  await aceptarTerminos(page, { ruta: RUTA_DE_TERMINOS })
  await expect(page.locator(SIDEBAR).first()).toBeVisible()
}

/** El proyecto `setup`: un login por rol, una sola vez por corrida, que deja `.auth/<rol>.json`. */
export function prepararSesiones(roles: Record<string, Credenciales>): void {
  for (const [rol, credenciales] of Object.entries(roles)) {
    base(`sesión de ${rol}`, async ({ page }) => {
      await entrarComo(page, credenciales)
      await page.context().storageState({ path: rutaAuth(rol) })
    })
  }
}
