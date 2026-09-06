import { ListaPrecioDetalle as ListaPrecioDetalleComercio } from 'libra-ui/comercio/ListaPrecioDetalle'
import { useAuth } from '../context/AuthContext'

// La pantalla vive en el kit desde P9-M2 (2026-09-06). Lo que decide este
// producto: el add-on mayorista habilita los quiebres por cantidad (una columna
// y un editor por producto); sin el add-on la lista es flat.
export function ListaPrecioDetalle() {
  const { user } = useAuth()
  return <ListaPrecioDetalleComercio conQuiebres={!!user?.modulos.includes('mayorista')} />
}
