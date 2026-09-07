import { VentaDetalle as VentaDetalleComercio } from 'libra-ui/comercio/VentaDetalle'
import { useAuth } from '../context/AuthContext'

// La pantalla vive en el kit desde P9-M3 (2026-09-06). Lo que decide este
// producto: quien puede anular es el rol admin de la sesion.
export function VentaDetalle() {
  const { user } = useAuth()
  return <VentaDetalleComercio puedeAnular={user?.role === 'admin'} />
}
