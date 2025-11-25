# contalibra
Sistema Contable</br>
- Version de prueba aun no en producción -

## Restaurar base de datos
Si ves errores como `Table 'contadb.proveedores' doesn't exist` o `Table 'contadb.logs' doesn't exist`, levanta la base de datos inicial ejecutando:

```bash
php scripts/setup_database.php
```

El script crea la base `contadb` (si no existe) y carga el esquema/demo desde `backup_temp.sql`.

Si tu instalación es anterior a los puntos de venta y ves errores como `Unknown column 'punto_venta_id' in 'field list'`, ejecuta la migración rápida que agrega las columnas y llaves faltantes en `cajas` y `ventas`:

```bash
php scripts/migrate_punto_venta_columns.php --base=contadb
```

Puedes cambiar el valor de `--base` si necesitas ejecutar la migración sobre la base de un tenant.

Si tu base de datos fue creada antes del flag de cambio de contraseña y aparece el error `Unknown column 'must_change_password'`, ejecuta la migración:

```bash
php scripts/migrate_must_change_password.php --base=contadb
```

Esto agrega la columna faltante en `usuarios` con un valor por defecto de 0.

## Notas sobre cajas
- La validación del usuario al abrir una caja se hace siempre contra la base maestra `contadb`.
- Si la base de datos del tenant no tiene el usuario replicado, se mostrará un error legible en lugar de fallar silenciosamente.

## Multiempresa y sucursales
El proyecto está preparado para aislar los datos de cada compañía y sucursal con bases separadas. Consulta `docs/arquitectura_multitenant.md` para ver las convenciones de nombres (`contadb`, `empresa_{id}_db`, `empresa_{id}_sucursal_{id}_db`) y el flujo recomendado de provisión de datos y permisos.
En `docs/estructura_empresa.md` encontrarás el detalle de las tablas y modelos PHP para gestionar la jerarquía empresa → sucursal → punto de venta y el inventario entre ellas.
