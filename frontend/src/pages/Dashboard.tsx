import { Dashboard as DashboardComercio } from 'libra-ui/comercio/Dashboard'

// La pantalla vive en el kit desde la fase 13 (2026-09-27); acá sólo se monta.
// Los valores por defecto del kit son los de Contalibra (accesos rápidos de
// factura, presupuesto, remito y movimiento de caja; facturas y presupuestos).
// Esta pantalla era una copia previa a la extracción: desde libra-ui v0.128.0
// toma los íconos del catálogo de indicadores (ADR-038).
export function Dashboard() {
  return <DashboardComercio />
}
