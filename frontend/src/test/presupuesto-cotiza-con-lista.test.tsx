// Slice 3 del paquete mayorista: el presupuesto cotiza con la lista de precios
// del cliente/elegida, no con el precio base.
//
// El mecanismo ya existia en el backend (`/productos/buscar?lista_id=...` devuelve
// el precio de la lista), pero PresupuestoForm no pasaba `lista_id`: cotizaba con
// el precio base. Un presupuesto que ignora la lista no tira ningun error -- da un
// numero, y da el numero equivocado. Por eso vive un test.
//
// Se usa el modo EDICION a proposito: al precargar el presupuesto, el `clienteId`
// queda seteado y dispara la preseleccion de la lista asignada al cliente (add-on
// mayorista) sin tener que operar los <Select>. Ese es el camino de una
// distribuidora: cliente con lista, y todo lo que se le presupuesta sale a esa lista.
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { PresupuestoForm } from '../pages/PresupuestoForm'

const CLIENTES = [{ id: 1, name: 'Distribuidora del Norte', activo: 1, cuit_dni: '', email: '', phone: '', address: '', iva_condition: '', auto_facturar: 0 }]
const LISTAS = [
  { id: 5, nombre: 'Mayorista', descripcion: '', activa: 1, es_default: 0, created_at: '' },
  { id: 6, nombre: 'Minorista', descripcion: '', activa: 1, es_default: 1, created_at: '' },
]
const PRESUPUESTO = {
  id: 1, numero: '1', client_id: 1, client_name: '', date: '2026-09-03',
  valid_until: '2026-10-03', tax_rate: 0.21, observations: '', estado: 'borrador',
  items: [{ description: 'Renglón a reemplazar', qty: 1, unit_price: 100 }],
  subtotal: 100, tax_amount: 21, total: 121,
}

let fetchMock: ReturnType<typeof vi.fn>

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
}

function montarEdicion({ listaAsignada, listas }: { listaAsignada: number | null; listas: unknown[] }) {
  fetchMock = vi.fn((url: string) => {
    const u = String(url)
    if (u.includes('/api/presupuestos/1')) return Promise.resolve(json(PRESUPUESTO))
    if (u.includes('/api/clientes/1/lista-precio')) return Promise.resolve(json({ lista_id: listaAsignada, lista: null }))
    if (u.includes('/api/clientes')) return Promise.resolve(json(CLIENTES))
    if (u.includes('/api/listas-precio')) return Promise.resolve(json(listas))
    if (u.includes('/productos/buscar')) {
      // Como el backend real: `precio_venta` es el de la lista sólo si se pasó
      // `lista_id`; sin él, es el base. Así el precio del renglón delata cuál se usó.
      const precio = u.includes('lista_id=') ? 80 : 100
      return Promise.resolve(json([{ id: 9, codigo: '', nombre: 'Fideos x500g', precio_venta: precio, precio_base: 100, unidad: 'u' }]))
    }
    return Promise.resolve(json([]))
  })
  vi.stubGlobal('fetch', fetchMock)
  return render(
    <MemoryRouter initialEntries={['/presupuestos/1/editar']}>
      <Routes>
        <Route path="/presupuestos/:id/editar" element={<PresupuestoForm />} />
        <Route path="/presupuestos/:id" element={<div>detalle</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('el presupuesto cotiza con la lista (add-on mayorista, slice 3)', () => {
  it('preselecciona la lista del cliente y cotiza el producto a esa lista', async () => {
    const usuario = userEvent.setup()
    montarEdicion({ listaAsignada: 5, listas: LISTAS })

    // La lista del cliente (id 5) quedó preseleccionada: el trigger la muestra.
    expect(await screen.findByText('Mayorista')).toBeInTheDocument()

    // Se busca un producto en el renglón: la búsqueda tiene que ir con lista_id=5.
    const desc = screen.getByDisplayValue('Renglón a reemplazar')
    await usuario.clear(desc)
    await usuario.type(desc, 'Fideos')

    const llamadas = fetchMock.mock.calls.map((c) => String(c[0]))
    expect(llamadas.some((u) => u.includes('/productos/buscar') && u.includes('lista_id=5'))).toBe(true)

    // Se elige la sugerencia y el precio unitario pasa a ser el de la lista (80),
    // no el base (100).
    await usuario.click(await screen.findByRole('button', { name: /Fideos x500g/ }))
    const numericos = screen.getAllByRole('spinbutton') as HTMLInputElement[]
    // [0] = cantidad, [1] = precio unitario del renglón.
    expect(numericos[1].value).toBe('80')
  })

  it('sin listas (modulo listas_precio apagado) no muestra el selector', async () => {
    montarEdicion({ listaAsignada: null, listas: [] })
    expect(await screen.findByDisplayValue('Renglón a reemplazar')).toBeInTheDocument()
    expect(screen.queryByText('Lista de precios')).not.toBeInTheDocument()
  })
})
