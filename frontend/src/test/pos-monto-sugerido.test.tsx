// El monto del medio de pago se completa solo con el total de la venta.
//
// Pedido del humano el 2026-08-20, después de cobrar en el mostrador: al elegir
// el medio, el importe tiene que estar puesto. Dividir el pago es la excepción y
// la decide el cajero; escribir el total a mano en cada venta es el caso normal
// y no debería costar nada.
//
// Se testea acá y no a ojo porque el valor que se autocompleta es el que **se
// manda al backend**: si la pantalla muestra $1.500 y el POST va con 0, la venta
// queda sin pagos y nadie lo nota hasta el arqueo.
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { AuthProvider } from '../context/AuthContext'

let fetchMock: ReturnType<typeof vi.fn>
let ultimoPost: { url: string; body: Record<string, unknown> } | null

beforeEach(() => {
  ultimoPost = null
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' },
  })
}

function montarPos() {
  fetchMock.mockImplementation((url: string, init?: RequestInit) => {
    const u = String(url)
    if (init?.method === 'POST' && u.includes('/api/ventas')) {
      ultimoPost = { url: u, body: JSON.parse(String(init.body)) }
      return Promise.resolve(json({ id: 1 }))
    }
    if (u.includes('/api/me')) {
      return Promise.resolve(json({
        id: '1', username: 'ana', name: 'Ana', role: 'admin', active: true,
        nombre: 'Ana', modulos: ['ventas'], empresa_nombre: 'Prueba',
        mp_pending_count: 0, comprobantes_pendientes_count: 0,
      }))
    }
    if (u.includes('/api/ventas/medios-pago')) {
      return Promise.resolve(json([
        { id: 'efectivo', label: 'Efectivo' },
        { id: 'mercadopago', label: 'Mercado Pago' },
      ]))
    }
    return Promise.resolve(json([]))
  })
  render(
    <MemoryRouter initialEntries={['/ventas']}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  )
}

async function abrirNuevaVentaConUnItem(user: ReturnType<typeof userEvent.setup>) {
  montarPos()
  await screen.findByRole('button', { name: /nueva venta/i })
  await user.click(screen.getByRole('button', { name: /nueva venta/i }))

  const precio = await screen.findByPlaceholderText('Precio')
  await user.clear(precio)
  await user.type(precio, '1500')
  const nombre = screen.getAllByPlaceholderText(/producto|descripci/i)[0]
  await user.type(nombre, 'Gaseosa')
  return { precio }
}

describe('el monto del pago se completa con el total', () => {
  it('sin tocar nada, el medio de pago ya trae el total de la venta', async () => {
    const user = userEvent.setup()
    await abrirNuevaVentaConUnItem(user)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Monto')).toHaveValue(1500)
    })
  })

  it('el importe autocompletado es el que se manda al backend', async () => {
    // La razón de ser de este archivo: que la pantalla muestre $1.500 no sirve
    // de nada si el POST viaja con 0 y la venta queda sin pagos.
    const user = userEvent.setup()
    await abrirNuevaVentaConUnItem(user)
    await waitFor(() => expect(screen.getByPlaceholderText('Monto')).toHaveValue(1500))

    await user.click(screen.getByRole('button', { name: /registrar venta/i }))

    await waitFor(() => expect(ultimoPost).not.toBeNull())
    // `cobrar_con_qr: false` viaja SIEMPRE, también en efectivo: el estado del
    // pago **se declara**, no se deja al default de la base. Ver `PagoPayload`
    // y la columna `ventas_pagos.estado`, que tiene default `'aprobado'` sólo
    // para poder backfillear las filas viejas.
    expect(ultimoPost!.body.pagos).toEqual([
      { medio: 'efectivo', monto: 1500, referencia: '', cobrar_con_qr: false },
    ])
  })

  // ⚠️ **Falta acá el test del check «Cobrar con QR ahora», y es deliberado.**
  //
  // Para ejercitarlo hay que cambiar el medio a MercadoPago, y el `Select` de
  // Radix **no se abre en jsdom**: el trigger consulta `hasPointerCapture`, que
  // jsdom no implementa, y el menú nunca aparece. Se probó con
  // `pointerEventsCheck: 0` y con el polyfill de `hasPointerCapture` en el
  // setup, y ninguno alcanzó.
  //
  // 🔴 Se descartó dejar sólo el negativo —"el check no está en efectivo"—
  // porque **pasaría igual si el check no existiera en ninguna parte**: sin su
  // positivo al lado no afirma nada.
  //
  // Lo que sí queda cubierto: que el campo viaja en el payload (el test de
  // arriba, con `cobrar_con_qr: false`), y del lado del backend el 422 cuando
  // llega en un medio que el QR no cobra, más los cuatro tests del circuito en
  // `tests/test_ventas_caja.py`. Lo único sin cubrir es que la pantalla oculte
  // el check, que es cosmético frente a eso.

  it('el monto escrito a mano no se pisa cuando cambia el total', async () => {
    const user = userEvent.setup()
    const { precio } = await abrirNuevaVentaConUnItem(user)

    const monto = screen.getByPlaceholderText('Monto')
    await user.clear(monto)
    await user.type(monto, '500')

    // El total sube; el importe escrito tiene que quedarse donde está.
    await user.clear(precio)
    await user.type(precio, '2000')

    await waitFor(() => expect(monto).toHaveValue(500))
  })
})
