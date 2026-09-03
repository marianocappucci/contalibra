// El add-on mayorista (slice 2): la ficha del cliente muestra un selector de
// lista de precios SOLO si la instancia tiene el modulo `mayorista` habilitado.
// Un selector que aparece donde no corresponde —o que no aparece donde si—
// no tira ningun error y no lo ve nadie hasta produccion; por eso vive un test.
//
// `modulos` llega en /api/me (AuthContext). El gate del backend es aparte
// (tests/test_mayorista_lista_cliente.py); esto cuida el gate de la UI.
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { AuthProvider } from '../context/AuthContext'

const CLIENTE = {
  id: 1, name: 'Distribuidora del Norte', cuit_dni: '30111111118',
  iva_condition: 'Responsable Inscripto', address: '', phone: '', email: '',
  auto_facturar: 0, active: 1, activo: 1,
  facturas: [], presupuestos: [], remitos: [], alias_facturacion: [],
}

const LISTAS = [
  { id: 5, nombre: 'Mayorista', descripcion: '', activa: 1, es_default: 0, created_at: '' },
  { id: 6, nombre: 'Minorista', descripcion: '', activa: 1, es_default: 1, created_at: '' },
]

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' },
  })
}

function montar({ modulos, listaAsignada }: { modulos: string[]; listaAsignada: number | null }) {
  fetchMock.mockImplementation((url: string) => {
    const u = String(url)
    if (u.includes('/api/me')) {
      return Promise.resolve(json({
        id: '1', username: 'ana', name: 'Ana', role: 'admin', active: true,
        nombre: 'Ana', modulos, empresa_nombre: 'Prueba', mp_pending_count: 0,
        comprobantes_pendientes_count: 0,
      }))
    }
    if (u.includes('/api/clientes/1/lista-precio')) {
      const lista = listaAsignada === null ? null : LISTAS.find((l) => l.id === listaAsignada)
      return Promise.resolve(json({ lista_id: listaAsignada, lista: lista ?? null }))
    }
    if (u.includes('/api/clientes/1')) return Promise.resolve(json(CLIENTE))
    if (u.includes('/api/listas-precio')) return Promise.resolve(json(LISTAS))
    return Promise.resolve(json([]))
  })
  render(
    <MemoryRouter initialEntries={['/clientes/1']}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('lista de precios del cliente (add-on mayorista)', () => {
  it('con el modulo habilitado muestra el selector con la lista asignada', async () => {
    montar({ modulos: ['clientes', 'mayorista'], listaAsignada: 5 })

    // Se espera al nombre del cliente para saber que la ficha monto. El nombre
    // sale mas de una vez (titulo y linea "Nombre / Razon social"), asi que
    // `findAllByText` -- la forma singular tira error ante mas de una coincidencia.
    expect(await screen.findAllByText('Distribuidora del Norte')).not.toHaveLength(0)
    expect(await screen.findByText('Lista de precios (mayorista)')).toBeInTheDocument()
    // El trigger del Select muestra la lista asignada (id 5 -> "Mayorista").
    expect(await screen.findByText('Mayorista')).toBeInTheDocument()
  })

  it('sin el modulo, la ficha no muestra ningun selector de lista', async () => {
    montar({ modulos: ['clientes'], listaAsignada: null })

    expect(await screen.findAllByText('Distribuidora del Norte')).not.toHaveLength(0)
    expect(screen.queryByText('Lista de precios (mayorista)')).not.toBeInTheDocument()
  })
})
