import { createLogin } from 'libra-ui/Login'
import { useAuth } from '../context/AuthContext'

export const Login = createLogin({
  productName: 'Contalibra',
  productInitial: 'C',
  redirectTo: '/dashboard',
  useAuth,
  formatError: (err) => err.detail,
  // Enlace "¿Olvidaste tu contraseña?" -- va de la mano con los endpoints
  // /api/forgot-password y /api/reset-password de web/api/auth.py.
  forgotPasswordPath: '/forgot-password',
  // Boton "Entrar a la demo". El prefijo es /api, no /auth: este producto
  // tiene su propio router (web/api/auth.py) en vez del de libraauth.
  // Declararlo aca NO alcanza para que se muestre: libra-ui consulta
  // GET /api/demo al montar y solo lo pinta si la instancia contesta que es
  // una demo -- en sistema.contalibra.com.ar esa ruta da 404.
  demoPath: '/api/demo',
})
