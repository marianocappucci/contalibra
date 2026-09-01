/** Configuración de Contalibra.
 *
 *  🔴 **Esta pantalla salió de acá.** Hasta el 2026-08-30 este archivo tenía
 *  987 líneas: la barra de pestañas, la sub-navegación de Integraciones, el
 *  botón de *Backup rápido*, los tutoriales de MercadoPago / ARCA / Gmail, y
 *  los formularios de las siete secciones. Era **la buena de la familia**, y
 *  ese era justamente el problema: los otros siete productos tenían pantallas
 *  distintas, y arreglar ésta no arreglaba ninguna.
 *
 *  Ahora el armado vive en `libra-ui/Configuracion` —calcado de lo que había
 *  acá— y este archivo declara lo que corresponde a este producto. El pedido
 *  del humano del 2026-08-29 es explícito sobre el porqué: *"si hago una
 *  modificación en la configuración o una actualización se actualice en
 *  todas"*.
 *
 *  ## Lo que este producto sigue teniendo propio
 *
 *  - **Ticket** y **Categorías**, que son suyas: MedLibra no imprime comandas y
 *    LibraDesk no tiene mostrador.
 *  🟢 **Del correo ya no queda nada propio.** La sección es la del kit desde el
 *    2026-08-30, y el botón *Probar conexión* también lo es desde `libra-ui`
 *    v0.55.0. Era lo último que este producto tenía envuelto: el botón existía
 *    acá y en el otro, y en los seis restantes no. Hoy el endpoint lo pone el
 *    motor (`libracore.smtp_router`) y lo montan los ocho, así que el
 *    envoltorio se retiró junto con `GET /api/email/probar`.
 *
 *  ## Lo que cambió del lado del backend
 *
 *  Se fue `GET /api/config`, que devolvía `config_manager.load()` **entero** —
 *  el token de MercadoPago y la contraseña de SMTP en el JSON de una pantalla.
 *  Su único consumidor era este archivo. Lo reemplazan lecturas acotadas y los
 *  routers del motor, que devuelven los secretos enmascarados.
 */
import { Package, Printer, Settings } from 'lucide-react'
import { createConfiguracion } from 'libra-ui/Configuracion'

import { CategoriasCard, TicketCard } from './config-secciones'

export const Config = createConfiguracion({
  // El icono que el sidebar de este producto le da a /configuracion.
  icono: Settings,
  // Sale en el tutorial de Gmail y en el de Padrón A13.
  producto: 'Contalibra',
  integraciones: {
    // Los prefijos son los que este producto ya publicó: cambiarlos rompería
    // el frontend desplegado sin ganar nada.
    mercadopago: { basePath: '/api/config/mercadopago' },
    // Sin `empresa`: este producto es multi-empresa y su fila se dio de alta
    // con la razón social, no con un slug fijo. El default `default` sólo se
    // usaría en una instancia sin ninguna fila.
    arca: { basePath: '/api/config/arca' },
    // Ver el docstring: el correo de este producto NO es el del kit.
    // 🟢 La seccion del kit, sin envoltorio. Hasta hoy este producto la
    // envolvia para agregarle el boton *Probar conexion*, que existia aca y en
    // el otro y en los seis restantes no. Desde libra-ui v0.55.0 el boton es
    // del kit y pega en `{basePath}/probar`, que es donde el motor monta el
    // endpoint: el envoltorio dejo de tener razon de ser.
    email: { basePath: '/api/config/smtp' },
  },
  propias: [
    { clave: 'ticket', label: 'Ticket / Impresora', icono: Printer, contenido: <TicketCard /> },
    { clave: 'categorias', label: 'Categorías', icono: Package, contenido: <CategoriasCard /> },
  ],
})

export default Config
