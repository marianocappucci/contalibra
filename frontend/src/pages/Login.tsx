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
})
