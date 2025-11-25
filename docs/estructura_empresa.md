# Estructura de empresa, sucursales y puntos de venta

Este proyecto ahora incluye una jerarquía explícita de **empresas → sucursales → puntos de venta** junto con inventario por sucursal y registro de transferencias/pedidos internos.

## Tablas nuevas

- `empresas`: catálogo corporativo con nombre y base de datos asociada.
- `usuarios`: ahora puede registrar `empresa_id` para asociar el usuario con la compañía propietaria.
- `sucursales`: ahora referencia a `empresas` vía `empresa_id` para agrupar sucursales.
- `puntos_venta`: puntos de venta físicos por sucursal (código opcional y estado activo/inactivo).
- `inventarios_sucursal`: stock por producto y sucursal con `actualizado_en`.
- `pedidos_sucursales` y `pedidos_sucursales_detalle`: pedidos internos entre sucursales.
- `transferencias_inventario`: bitácora de movimientos entre sucursales (opcionalmente vinculada a un pedido).
- `cajas` y `ventas`: incorporan `punto_venta_id` para amarrar las operaciones al punto de venta que las generó.

## Modelos PHP

- `modelo/Empresa.php`: CRUD de empresas, árbol de sucursales con puntos de venta e inventario consolidado de la empresa.
- `modelo/Sucursal.php`: CRUD de sucursales con asignación opcional a empresa.
- `modelo/PuntoVenta.php`: CRUD de puntos de venta por sucursal.
- `modelo/InventarioSucursal.php`: stock por sucursal, transferencias y pedidos internos (creación, atención y trazabilidad).
- `modelo/Venta.php`: registra ventas asociándolas a sucursal/punto de venta y descuenta stock tanto general como por sucursal.
- `modelo/Caja.php`: apertura de caja vinculada a un punto de venta y visualización del nombre del PV.

## Flujo típico

1. Crear la empresa con `Empresa::create` y sus sucursales (ya sea con `Sucursal::create` o desde la UI existente).
2. Registrar puntos de venta por sucursal con `PuntoVenta::create`.
3. Usar `InventarioSucursal::ajustarStock` para subir inventario inicial por sucursal.
4. Registrar ventas indicando `sucursal_id` y, opcionalmente, `punto_venta_id`; el modelo descuenta stock por sucursal.
5. Para mover stock entre sucursales, usar `InventarioSucursal::registrarPedido` y luego `InventarioSucursal::atenderPedido`, lo que genera transferencias y actualiza saldos.
6. Consultar el consolidado por empresa con `Empresa::inventarioTotal`.
