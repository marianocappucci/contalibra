import { createLogin } from 'libra-ui/Login'
import { useAuth } from '../context/AuthContext'

export const Login = createLogin({
  productName: 'Contalibra',
  productInitial: 'C',
  redirectTo: '/dashboard',
  useAuth,
  formatError: (err) => err.detail,
})
