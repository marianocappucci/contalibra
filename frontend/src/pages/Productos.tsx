import { Productos as ProductosComercio } from 'libra-ui/comercio/Productos'

// La pantalla vive en el kit desde P9-M1 (2026-09-06). Lo que decide este
// producto: distingue producto de servicio (un servicio se factura pero no
// tiene inventario).
export function Productos() {
  return <ProductosComercio conTipo />
}
