// La bandeja de comprobantes a facturar.
//
// La regla que sólo se puede probar acá es la del agrupado: se pueden tildar
// varios comprobantes juntos, pero **sólo del mismo cliente**, porque una
// factura tiene un solo receptor. El backend lo rechaza igual con un 422, pero
// dejar tildar lo que después va a fallar es una trampa — lo que se fija es que
// la pantalla no la tienda.
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ComprobantesPendientes } from '../pages/ComprobantesPendientes'

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

function montar() {
  return render(
    <MemoryRouter>
      <ComprobantesPendientes />
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
