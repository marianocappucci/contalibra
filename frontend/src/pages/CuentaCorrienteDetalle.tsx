import { CuentaCorrienteDetalle as CuentaCorrienteDetalleComercio } from 'libra-ui/comercio/CuentaCorrienteDetalle'
import { useAuth } from '../context/AuthContext'

// La pantalla vive en el kit desde P9-M4 (2026-09-07). Lo que decide este
// producto: el rol admin borra pagos, y al cobrar se emite y se abre el recibo
// de cobranza (`con_recibos` en el backend).
export function CuentaCorrienteDetalle() {
  const { user } = useAuth()
  return <CuentaCorrienteDetalleComercio esAdmin={user?.role === 'admin'} conRecibos />
}
