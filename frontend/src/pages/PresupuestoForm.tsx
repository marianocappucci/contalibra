import { PresupuestoForm as PresupuestoFormKit } from 'libra-ui/PresupuestoForm'
import { useAuth } from '../context/AuthContext'

// La pantalla vive en el kit desde el pase de comprobantes al kit (2026-09-07). Lo que decide este
// producto: el re-precio por cantidad es del add-on mayorista (ver
// plans.py::ADDONS) y `modulos` llega en /api/auth. El selector de lista NO
// va por acá: lo gatea el backend con un 403 del módulo `listas_precio`.
export function PresupuestoForm() {
  const { user } = useAuth()
  return <PresupuestoFormKit conSelectorDeLista conQuiebres={!!user?.modulos.includes('mayorista')} />
}
