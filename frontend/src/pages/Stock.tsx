import { Stock as StockComercio } from 'libra-ui/comercio/Stock'

// La pantalla vive en el kit desde P9-M1 (2026-09-06). Sin props: fijar /
// entrada / salida, y el historial desplegado en la misma pantalla. La merma
// no aparece porque este producto no declara motivos.
export function Stock() {
  return <StockComercio />
}
