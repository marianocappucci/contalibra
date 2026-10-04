import { VentaDetalle as VentaDetalleComercio } from 'libra-ui/comercio/VentaDetalle'
import { useAuth } from '../context/AuthContext'

// La pantalla vive en el kit desde P9-M3 (2026-09-06). Lo que decide este
// producto: quien puede anular y quien puede emitir la nota de crédito es el
// rol admin de la sesion. La nota (libracore v1.129.0, `POST /api/facturas/{id}/nota-credito`,
// solo admin en el backend) la exige antes de anular una venta cuya factura tiene
// CAE (libracommerce v0.41.0, ADR-032).
export function VentaDetalle() {
  const { user } = useAuth()
  const esAdmin = user?.role === 'admin'
  return <VentaDetalleComercio puedeAnular={esAdmin} puedeEmitirNota={esAdmin} />
}
