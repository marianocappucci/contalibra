# Arquitectura multibase para compañías y sucursales

Este proyecto utiliza un esquema de bases aisladas para minimizar la fuga de datos entre clientes.
La estructura contempla una base maestra y bases independientes por compañía y sucursal.

## Bases de datos y convenciones de nombres

- **Base maestra**: `contadb` (configurada en `config/config.php`). Guarda el usuario root, catálogo de compañías y cualquier dato centralizado.
- **Base por compañía**: `empresa_{empresaId}_db`.
- **Base por sucursal**: `empresa_{empresaId}_sucursal_{sucursalId}_db`.

Los helpers de `TenantContext` generan estos nombres de forma consistente:
- `TenantContext::databaseNameForEmpresa($empresaId)` → `empresa_{empresaId}_db`.
- `TenantContext::databaseNameForSucursal($empresaId, $sucursalId)` → `empresa_{empresaId}_sucursal_{sucursalId}_db`.

## Resolución de base activa

La clase `TenantContext` decide qué base usar en cada request, con la siguiente prioridad:
1. `$_SESSION['db_name']` (por ejemplo, fijada al autenticar o al elegir manualmente una base).
2. Contexto de sucursal activo (`empresa_id` + `sucursal_id`).
3. Contexto de empresa activo (`empresa_id`).
4. Base maestra `contadb` como último recurso.

`config/database.php` invoca `TenantContext::activeDatabaseName()` para resolver la base antes de abrir la conexión PDO, por lo que la separación se respeta en toda la app.

## Escenario de datos

- **Usuarios root/administradores** viven en la base maestra; se pueden replicar a cada base de compañía/sucursal según sea necesario.
- **Productos** se almacenan a nivel compañía (base `empresa_{id}_db`) y pueden compartir stock general para reportes corporativos.
- **Stock** se maneja en dos niveles:
  - Stock general de la compañía en `empresa_{id}_db`.
  - Stock específico por sucursal en `empresa_{id}_sucursal_{sucursalId}_db`.
- **Cajas y ventas** se registran únicamente en la base de la sucursal.

## Reportería y permisos

- **Administrador de empresa**: consulta los reportes consolidados en la base de compañía (`empresa_{id}_db`), con agregaciones de todas las sucursales.
- **Encargado de sucursal**: accede solo a la base de su sucursal (`empresa_{id}_sucursal_{sucursalId}_db`) y ve datos aislados.

## Pasos recomendados de aprovisionamiento

1. Crear la base maestra `contadb` (si no existe) y registrar las compañías.
2. Para cada compañía (ID `N`):
   - Crear `empresa_N_db` y cargar el esquema base sin usuarios sensibles.
   - Registrar productos y stock general.
3. Para cada sucursal de la compañía (ID `S`):
   - Crear `empresa_N_sucursal_S_db` a partir del mismo esquema.
   - Configurar usuarios locales (encargados) y las cajas iniciales.
4. Al autenticar, establecer `TenantContext::setContext($empresaId, $sucursalId)` según el perfil del usuario. Los administradores pueden fijar solo `empresaId` para ver el consolidado.

Esta guía permite mantener aislamiento completo entre compañías y sucursales, al tiempo que habilita reportes corporativos y operaciones locales independientes.
