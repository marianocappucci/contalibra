// Shim sobre libra-ui/PasswordReset (mismo patrón que Login).
//
// `basePath: '/api'` y no el default '/auth': Contalibra no monta el router
// de libraauth, tiene sus propios endpoints JSON en `web/api/auth.py` bajo el
// prefijo `/api` (igual que `/api/login`).
//
// Las dos pantallas son públicas: van fuera del guard de sesión en App.tsx,
// porque quien las usa justamente no puede entrar.
import { createForgotPassword, createResetPassword } from 'libra-ui/PasswordReset'

const branding = { productName: 'Contalibra', productInitial: 'C', basePath: '/api' }

// El pedido del mail lleva el mismo captcha ALTCHA que el login: sin él, el
// endpoint manda correos a pedido de cualquiera. El reset-password no lo
// lleva: ya lo gatea el token que llegó por mail.
export const ForgotPassword = createForgotPassword({ ...branding, captchaPath: '/api/captcha' })
export const ResetPassword = createResetPassword(branding)
