// Slice 4: el editor de quiebres por cantidad en la lista de precios.
//
// La columna «Quiebres» y su modal son del add-on mayorista: aparecen sólo si la
// instancia tiene el módulo. El gate del backend es aparte
// (tests/test_mayorista_quiebres.py); esto cuida el gate de la UI.
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ListaPrecioDetalle } from '../pages/ListaPrecioDetalle'
import { AuthProvider } from '../context/AuthContext'

const LISTA = { id: 1, nombre: 'Mayorista', descripcion: '', activa: 1, es_default: 0, created_at: '' }
const ITEMS = [{
  id: 9, codigo: 'FID', nombre: 'Fideos x500g', unidad: 'u', categoria: '',
  precio_venta: 100, precio_costo: 50, precio_lista: 80, en_lista: 1,
}]

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
}

function montar(modulos: string[]) {
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    const u = String(url)
    if (u.includes('/api/me')) {
      return Promise.resolve(json({
        id: '1', username: 'ana', name: 'Ana', role: 'admin', active: true,
        nombre: 'Ana', modulos, empresa_nombre: 'Prueba', mp_pending_count: 0,
        comprobantes_pendientes_count: 0,
      }))
    }
    if (u.includes('/api/listas-precio/1/items/9/quiebres')) return Promise.resolve(json([]))
    if (u.includes('/api/listas-precio/1/items')) return Promise.resolve(json(ITEMS))
    if (u.includes('/api/listas-precio')) return Promise.resolve(json([LISTA]))
    if (u.includes('/api/productos/categorias')) return Promise.resolve(json([]))
    return Promise.resolve(json([]))
  }))
  render(
    <MemoryRouter initialEntries={['/listas-precio/1']}>
      <AuthProvider>
        <Routes>
          <Route path="/listas-precio/:id" element={<ListaPrecioDetalle />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('editor de quiebres por cantidad (add-on mayorista)', () => {
  it('con el módulo, cada producto tiene un botón de quiebres que abre el editor', async () => {
    const usuario = userEvent.setup()
    montar(['listas_precio', 'mayorista'])

    // Se espera al producto para saber que la tabla montó.
    expect(await screen.findByText('Fideos x500g')).toBeInTheDocument()
    const boton = await screen.findByRole('button', { name: 'Quiebres' })
    await usuario.click(boton)

    expect(await screen.findByText('Quiebres por cantidad')).toBeInTheDocument()
    expect(await screen.findByText(/Sin quiebres/)).toBeInTheDocument()
  })

  it('sin el módulo, no hay columna ni botón de quiebres', async () => {
    montar(['listas_precio'])
    expect(await screen.findByText('Fideos x500g')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Quiebres' })).not.toBeInTheDocument()
  })
})
