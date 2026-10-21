// La bandeja de comprobantes a facturar (la pantalla es de libra-ui desde la v0.173.0; acá se prueba lo que cablea este
// producto: el formulario de factura al que lleva «Facturar» y el permiso de descartar por rol).
//
// La regla que sólo se puede probar acá es la del agrupado: se pueden tildar
// varios comprobantes juntos, pero **sólo del mismo cliente**, porque una
// factura tiene un solo receptor. El backend lo rechaza igual con un 422, pero
// dejar tildar lo que después va a fallar es una trampa — lo que se fija es que
// la pantalla no la tienda.
import { render, screen, waitFor } from '@testing-library/react'
import { useEffect } from 'react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ComprobantesPendientes } from '../pages/ComprobantesPendientes'

// El rol sale de `useAuth`: se fija por test, sin montar el AuthProvider (trae el gate de Términos y su propia ronda de
// pedidos, ajenos a lo que se mide acá).
let rol: 'admin' | 'operador' | 'cajero' = 'admin'
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: '1', username: 'u', role: rol } }),
}))

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  rol = 'admin'
  fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
})

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' },
  })
}

function comprobante(over: Record<string, unknown> = {}) {
  return {
    id: 1,
    origen_producto: 'libradesk',
    origen_instancia: 'compulibra',
    origen_tipo: 'cuota_contrato',
    origen_id: '1',
    cliente_id: null,
    cliente_cuit: '30-71234567-9',
    cliente_razon: 'Ferretería San Martín',
    cliente_domicilio: '',
    periodo_desde: '2026-08-01',
    periodo_hasta: '2026-08-31',
    concepto: 'Alquiler',
    condicion_venta: 'Contado',
    observaciones: '',
    items: [{ description: 'Alquiler impresora', qty: 1, unit_price: 45000, iva_rate: 0.21 }],
    total: 54450,
    estado: 'pendiente',
    factura_id: null,
    motivo_descarte: '',
    resuelto_at: '',
    resuelto_por: '',
    created_at: '2026-09-01 10:00:00',
    ...over,
  }
}

function conBandeja(pendientes: unknown[]) {
  fetchMock.mockImplementation(() => Promise.resolve(json({
    pendientes, facturados: [], descartados: [], total_pendientes: pendientes.length,
  })))
}

// Donde cae «Facturar»: el formulario de factura, con el `state` que arma la página.
let estadoDelFormulario: Record<string, unknown> | null = null

function FormularioDeFactura() {
  const state = useLocation().state as Record<string, unknown> | null
  useEffect(() => { estadoDelFormulario = state }, [state])
  return <p>Formulario de factura</p>
}

function montar() {
  estadoDelFormulario = null
  return render(
    <MemoryRouter initialEntries={['/comprobantes-pendientes']}>
      <Routes>
        <Route path="/comprobantes-pendientes" element={<ComprobantesPendientes />} />
        <Route path="/facturas/nuevo" element={<FormularioDeFactura />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('bandeja de comprobantes a facturar', () => {
  it('muestra lo que otro sistema dejó pendiente', async () => {
    conBandeja([comprobante()])
    montar()
    expect(await screen.findByText('Ferretería San Martín')).toBeInTheDocument()
    expect(screen.getByText('Cuota de contrato')).toBeInTheDocument()
  })

  it('avisa cuando no hay nada esperando', async () => {
    conBandeja([])
    montar()
    expect(await screen.findByText(/No hay nada esperando para facturar/)).toBeInTheDocument()
  })

  // Las casillas se vuelven a consultar después de cada click: la tabla se
  // rerenderiza y los nodos de antes quedan desprendidos del documento, así que
  // un `expect` sobre la referencia vieja mide un DOM que ya no existe — pasó
  // escribiendo estos tests, y el guard parecía roto cuando andaba.
  const casilla = (i: number) => screen.getAllByRole('checkbox')[i]

  it('deja tildar dos comprobantes del mismo cliente', async () => {
    conBandeja([
      comprobante({ id: 1, origen_id: '1' }),
      comprobante({ id: 2, origen_id: '2' }),
    ])
    montar()
    await screen.findAllByText('Ferretería San Martín')

    await userEvent.click(casilla(0))
    await userEvent.click(casilla(1))

    expect(await screen.findByText(/2 comprobantes elegidos/)).toBeInTheDocument()
  })

  it('bloquea el de otro cliente en cuanto se tilda uno', async () => {
    conBandeja([
      comprobante({ id: 1, origen_id: '1' }),
      comprobante({
        id: 2, origen_id: '2', cliente_cuit: '27-99999999-4', cliente_razon: 'Otra SRL',
      }),
    ])
    montar()
    await screen.findByText('Otra SRL')

    // Antes de elegir nada, los dos se pueden tildar.
    expect(casilla(1)).toBeEnabled()

    await userEvent.click(casilla(0))

    // El de Otra SRL queda deshabilitado: una factura tiene un solo receptor.
    await waitFor(() => expect(casilla(1)).toBeDisabled())
    expect(screen.getByText(/1 comprobante elegido/)).toBeInTheDocument()
  })

  it('destildar el último vuelve a habilitar a los otros clientes', async () => {
    conBandeja([
      comprobante({ id: 1, origen_id: '1' }),
      comprobante({
        id: 2, origen_id: '2', cliente_cuit: '27-99999999-4', cliente_razon: 'Otra SRL',
      }),
    ])
    montar()
    await screen.findByText('Otra SRL')

    await userEvent.click(casilla(0))
    await waitFor(() => expect(casilla(1)).toBeDisabled())

    await userEvent.click(casilla(0))
    await waitFor(() => expect(casilla(1)).toBeEnabled())
  })

  it('el total elegido es la suma de lo tildado', async () => {
    conBandeja([
      comprobante({ id: 1, origen_id: '1', total: 1000 }),
      comprobante({ id: 2, origen_id: '2', total: 500 }),
    ])
    montar()
    await screen.findAllByText('Ferretería San Martín')

    await userEvent.click(casilla(0))
    await userEvent.click(casilla(1))

    expect(await screen.findByText(/1\.500,00/)).toBeInTheDocument()
  })
})

describe('lo que cablea este producto en la bandeja', () => {
  const prefill = (over: Record<string, unknown> = {}) => ({
    comprobantes_ids: [1, 2], avisos: ['Dos períodos distintos'], concepto: 2, condicion_venta: 'Contado', tax_rate: 21,
    client_id: 7, client_name: 'Ferretería San Martín', client_cuit: '30-71234567-9', client_address: '', fecha: '2026-09-01',
    observations: 'Alquiler', items: [{ description: 'Alquiler impresora', qty: 2, unit_price: 45000 }],
    fch_serv_desde: '2026-08-01', fch_serv_hasta: '2026-08-31', fch_vto_pago: '2026-09-10', ...over,
  })

  function conPrefill(cuerpo: unknown) {
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (String(url).includes('/facturar-prefill') && init?.method === 'POST') return Promise.resolve(json(cuerpo))
      return Promise.resolve(json({
        pendientes: [comprobante({ id: 1, origen_id: '1' }), comprobante({ id: 2, origen_id: '2' })],
        facturados: [], descartados: [], total_pendientes: 2,
      }))
    })
  }

  it('«Facturar» pide el prefill con los ids elegidos y lleva al formulario con el mismo state de siempre', async () => {
    conPrefill(prefill())
    montar()
    await screen.findAllByText('Ferretería San Martín')
    await userEvent.click(screen.getAllByRole('checkbox')[0])
    await userEvent.click(screen.getAllByRole('checkbox')[1])
    await userEvent.click(screen.getByRole('button', { name: /^Facturar$/ }))

    expect(await screen.findByText('Formulario de factura')).toBeInTheDocument()
    const pedido = fetchMock.mock.calls.find(([u]) => String(u).includes('/facturar-prefill'))!
    expect(String(pedido[0])).toBe('/api/comprobantes-pendientes/facturar-prefill')
    expect(JSON.parse(String((pedido[1] as RequestInit).body))).toEqual({ ids: [1, 2] })
    expect(estadoDelFormulario).toEqual({
      clienteId: '7',
      clienteNombreLibre: '',
      concepto: '2',
      condicionVenta: 'Contado',
      taxRate: '21',
      observations: 'Alquiler',
      items: [{ description: 'Alquiler impresora', qty: '2', unit_price: '45000' }],
      fchServDesde: '2026-08-01',
      fchServHasta: '2026-08-31',
      fchVtoPago: '2026-09-10',
      comprobantesPendientesIds: [1, 2],
      avisos: ['Dos períodos distintos'],
    })
  })

  it('un cliente que no está dado de alta va por nombre libre y no por id', async () => {
    conPrefill(prefill({ client_id: null, client_name: 'Consumidor ocasional' }))
    montar()
    await screen.findAllByText('Ferretería San Martín')
    await userEvent.click(screen.getAllByRole('checkbox')[0])
    await userEvent.click(screen.getByRole('button', { name: /^Facturar$/ }))

    await screen.findByText('Formulario de factura')
    expect(estadoDelFormulario).toMatchObject({ clienteId: '', clienteNombreLibre: 'Consumidor ocasional' })
  })

  it('el admin descarta', async () => {
    conBandeja([comprobante()])
    montar()
    await screen.findByText('Ferretería San Martín')
    expect(screen.getByTitle('Descartar')).toBeInTheDocument()
  })

  it('quien no es admin no ve «Descartar»', async () => {
    rol = 'cajero'
    conBandeja([comprobante()])
    montar()
    await screen.findByText('Ferretería San Martín')
    expect(screen.queryByTitle('Descartar')).not.toBeInTheDocument()
  })
})

// Las ventas que el nodo offline cobró sin conexión (libra-ui ADR-077, E6 de LibraEdge). Aparecen en la misma bandeja
// pero no se juntan en el formulario: se facturan desde la venta. Fuera de un nodo no hay ninguna, y lo de arriba es lo
// que ve Compulibra.
describe('bandeja con ventas del nodo offline', () => {
  const ventaDelNodo = (over: Record<string, unknown> = {}) => comprobante({
    id: 9, origen_producto: 'contalibra', origen_instancia: 'nodo-1', origen_tipo: 'venta', origen_id: '41',
    cliente_cuit: '', cliente_razon: 'Consumidor Final', periodo_desde: '', periodo_hasta: '', ...over,
  })

  it('la rotula como venta sin conexión y no la deja tildar', async () => {
    conBandeja([comprobante({ id: 1, origen_id: '1' }), ventaDelNodo()])
    montar()
    await screen.findByText('Consumidor Final')

    expect(screen.getByText('Venta sin conexión')).toBeInTheDocument()
    // Una sola casilla: la del comprobante de LibraDesk. La venta lleva el botón.
    expect(screen.getAllByRole('checkbox')).toHaveLength(1)
    expect(screen.getByRole('button', { name: /Facturar ahora/ })).toBeInTheDocument()
  })

  it('no ofrece descartar una venta del nodo (ya está cobrada: se factura)', async () => {
    conBandeja([comprobante({ id: 1, origen_id: '1' }), ventaDelNodo()])
    montar()
    await screen.findByText('Consumidor Final')
    // Un solo «Descartar»: el del comprobante de LibraDesk.
    expect(screen.getAllByTitle('Descartar')).toHaveLength(1)
  })

  it('«Facturar ahora» factura las del nodo y recarga la bandeja', async () => {
    let bandeja: unknown[] = [ventaDelNodo()]
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url.includes('/api/nodo/facturar-pendientes') && init?.method === 'POST') {
        bandeja = []
        return Promise.resolve(json({
          es_nodo: true, en_linea: true, facturadas: [{ venta_id: 41, factura_id: 3, cae: '70000000000001' }],
          descartadas: [], errores: [], quedan: 0,
        }))
      }
      if (url.includes('/api/nodo/conexion')) {
        return Promise.resolve(json({ es_nodo: true, en_linea: true, node_id: 'nodo-1', a_facturar: 0 }))
      }
      return Promise.resolve(json({ pendientes: bandeja, facturados: [], descartados: [], total_pendientes: bandeja.length }))
    })
    montar()
    await screen.findByText('Consumidor Final')

    await userEvent.click(screen.getByRole('button', { name: /Facturar ahora/ }))

    expect(await screen.findByText(/No hay nada esperando para facturar/)).toBeInTheDocument()
    const posts = fetchMock.mock.calls.filter(([u, i]) => String(u).includes('/api/nodo/facturar-pendientes')
      && (i as RequestInit | undefined)?.method === 'POST')
    expect(posts).toHaveLength(1)
  })

  it('sin ventas del nodo la bandeja no pregunta nada del nodo', async () => {
    conBandeja([comprobante()])
    montar()
    await screen.findByText('Ferretería San Martín')
    expect(screen.queryByRole('button', { name: /Facturar ahora/ })).not.toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes('/api/nodo'))).toBe(false)
  })
})
