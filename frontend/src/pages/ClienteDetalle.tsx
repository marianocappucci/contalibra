import { ClienteDetalle as ClienteDetalleComercio } from 'libra-ui/comercio/ClienteDetalle'
import { useAuth } from '../context/AuthContext'

// La pantalla vive en el kit desde P9-M4 (2026-09-07). Lo que decide este
// producto: la lista de precio del cliente se muestra si la instancia tiene el
// add-on mayorista (ver plans.py::ADDONS); `modulos` llega en /api/auth.
export function ClienteDetalle() {
  const { user } = useAuth()
  return <ClienteDetalleComercio conListaDePrecio={!!user?.modulos.includes('mayorista')} />
}
