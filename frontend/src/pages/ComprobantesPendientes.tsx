import { useNavigate } from 'react-router-dom'
import { BandejaDeComprobantes } from 'libra-ui/BandejaDeComprobantes'
import type { PrefillComprobantes } from 'libra-ui/comprobantes-pendientes'
import { useAuth } from '../context/AuthContext'

// La pantalla vive en el kit desde libra-ui v0.173.0 (ADR-087): la tabla, las casillas del mismo cliente, el descarte y
// las ventas que el nodo offline cobró sin conexión. Lo que decide este producto es qué hace «Facturar» (llevar al
// formulario de factura con todo cargado: la emisión y el CAE pasan ahí, la bandeja nunca factura por su cuenta) y quién
// puede descartar (el rol admin de la sesión).
export function ComprobantesPendientes() {
  const navigate = useNavigate()
  const { user } = useAuth()

  function alFacturar(prefill: PrefillComprobantes) {
    navigate('/facturas/nuevo', {
      state: {
        clienteId: prefill.client_id ? String(prefill.client_id) : '',
        clienteNombreLibre: prefill.client_id ? '' : prefill.client_name,
        concepto: String(prefill.concepto),
        condicionVenta: prefill.condicion_venta,
        taxRate: String(prefill.tax_rate),
        observations: prefill.observations,
        items: prefill.items.map((i) => ({
          description: i.description, qty: String(i.qty), unit_price: String(i.unit_price),
        })),
        fchServDesde: prefill.fch_serv_desde,
        fchServHasta: prefill.fch_serv_hasta,
        fchVtoPago: prefill.fch_vto_pago,
        comprobantesPendientesIds: prefill.comprobantes_ids,
        avisos: prefill.avisos,
      },
    })
  }

  return <BandejaDeComprobantes alFacturar={alFacturar} puedeDescartar={user?.role === 'admin'} />
}
