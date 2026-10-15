import { expect, SIDEBAR, test } from 'libra-ui/e2e'
import { json } from './datos'
import { INICIO_POR_ROL, MENU_POR_ROL, PROHIBIDAS_AL_QUE_NO_ES_ADMIN } from './menus'
import { ROLES, type Rol } from './roles'
import { entrarComo } from './sesion'

// El login de cada rol, por la pantalla y sin sesión previa (el proyecto `setup` también entra por ahí, pero acá es lo que se
// prueba): cada uno cae en su pantalla inicial, ve SU menú y ni más ni menos, y lo que es sólo del admin no se ofrece.
//
// 🔴 La SPA de Contalibra sólo decide qué se OFRECE (`adminOnly` del Layout); el que corta de verdad es el servidor. A diferencia de
// VentaLibra, un link directo a una pantalla de admin NO redirige: la abre con el cuerpo vacío y un «No autorizado». Por eso acá la
// pregunta de fondo se le hace a la API con la sesión que recién abrió el navegador (403 y no los datos), y a la pantalla se le
// pide que no muestre nada ajeno.
test.use({ rol: null })

for (const rol of Object.keys(ROLES) as Rol[]) {
  test(`${rol}: entra, cae en su inicio, ve su menú y no entra a lo que no tiene`, async ({ page, apiDe }) => {
    await entrarComo(page, ROLES[rol])
    // Tras el login la raíz resuelve el inicio de cada rol.
    await page.goto('/')
    await expect(page).toHaveURL(new RegExp(`${INICIO_POR_ROL[rol]}$`))
    await expect(page.locator(SIDEBAR).first()).toBeVisible()

    const enlaces = await page.locator(`${SIDEBAR} a`).evaluateAll((as) => as.map((a) => a.getAttribute('href') ?? ''))
    expect([...new Set(enlaces)].sort()).toEqual([...MENU_POR_ROL[rol]].sort())

    if (rol === 'admin') {
      // El control de abajo al revés: lo mismo que se le corta al resto, el admin lo recibe.
      const api = await apiDe('admin')
      for (const { endpoint } of PROHIBIDAS_AL_QUE_NO_ES_ADMIN) {
        const respuesta = await api.get(endpoint)
        expect(respuesta.status(), `admin: GET ${endpoint}`).toBe(200)
      }
      return
    }

    for (const { ruta, endpoint } of PROHIBIDAS_AL_QUE_NO_ES_ADMIN) {
      // El servidor la corta: 403 y no los datos.
      const respuesta = await page.request.get(endpoint)
      expect(respuesta.status(), `${rol}: GET ${endpoint}`).toBe(403)
      // Y el link directo no le muestra nada de lo que hay: la pantalla no se pasa por una a la que tiene acceso.
      await page.goto(ruta)
      await expect(page).toHaveURL(new RegExp(`${ruta}$`))
      await expect(page.locator(SIDEBAR).first()).toBeVisible()
      // Ni los usuarios, que es lo que esa pantalla lista: el `admin` (que nadie más que él puede ver) no aparece.
      if (ruta === '/usuarios') await expect(page.getByText('admin', { exact: true })).toHaveCount(0)
    }
  })
}

test('lo que no es del admin se corta también al escribir, no sólo al leer', async ({ apiDe }) => {
  // Un operador y un cajero no pueden dar de alta un usuario ni cambiar los datos de la empresa: sin esto, el menú que los esconde
  // sería lo único entre ellos y la configuración de la instancia.
  for (const rol of ['operador', 'cajero'] as const) {
    const api = await apiDe(rol)
    const alta = await api.post('/api/usuarios', {
      data: { username: `intruso_${rol}`, name: 'Intruso', password: 'una-clave-larga-123', role: 'admin' },
    })
    expect(alta.status(), `${rol}: POST /api/usuarios`).toBe(403)
    const empresa = await api.put('/api/config/empresa', { data: { nombre: 'Tomada' } })
    expect(empresa.status(), `${rol}: PUT /api/config/empresa`).toBe(403)
  }
  // Y no quedó nada hecho a medias: el usuario que intentaron crear no existe.
  const admin = await apiDe('admin')
  const usuarios = await json<Array<{ username: string }>>(await admin.get('/api/usuarios'), 'GET /api/usuarios')
  expect(usuarios.map((u) => u.username).filter((u) => u.startsWith('intruso_'))).toEqual([])
})

// 🔴 DEFECTO REAL (2026-10-15, medido en esta rama): un operador o un cajero que entra por link directo a una pantalla de admin ve
// «No autorizado» pero, debajo, el estado vacío como si no hubiera nada: «Sin usuarios todavía.» (hay tres), «No hay cuentas creadas
// aún. Crear primera cuenta» en Tesorería, y en `/comprobantes-pendientes` ni siquiera el «No autorizado» (el 403 se traga y queda
// «No hay nada esperando para facturar.»). No filtra datos (el servidor corta), pero miente. Lo correcto: redirigir al inicio como
// VentaLibra, o al menos no pintar el vacío. Se pone en `fixme` hasta que se decida; el arreglo va en libra-ui (las pantallas son del kit).
test.describe('un link directo a una pantalla de admin no se hace pasar por una pantalla vacía', () => {
  test.fixme(true, 'defecto de la app: muestra «No autorizado» y además el estado vacío («Sin usuarios todavía.»)')
  test.use({ rol: 'operador' })

  test('/usuarios y /comprobantes-pendientes', async ({ page }) => {
    await page.goto('/usuarios')
    await expect(page.getByText('No autorizado')).toBeVisible()
    await expect(page.getByText('Sin usuarios todavía.')).toHaveCount(0)
    await page.goto('/comprobantes-pendientes')
    await expect(page.getByText('No autorizado')).toBeVisible()
    await expect(page.getByText('No hay nada esperando para facturar.')).toHaveCount(0)
  })
})
