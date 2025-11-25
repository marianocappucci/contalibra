# contalibra
Sistema Contable</br>
- Version de prueba aun no en producción -

## Restaurar base de datos
Si ves errores como `Table 'contadb.proveedores' doesn't exist` o `Table 'contadb.logs' doesn't exist`, levanta la base de datos inicial ejecutando:

```bash
php scripts/setup_database.php
```

El script crea la base `contadb` (si no existe) y carga el esquema/demo desde `backup_temp.sql`.

## Notas sobre cajas
- La validación del usuario al abrir una caja se hace siempre contra la base maestra `contadb`.
- Si la base de datos del tenant no tiene el usuario replicado, se mostrará un error legible en lugar de fallar silenciosamente.

## Multiempresa y sucursales
El proyecto está preparado para aislar los datos de cada compañía y sucursal con bases separadas. Consulta `docs/arquitectura_multitenant.md` para ver las convenciones de nombres (`contadb`, `empresa_{id}_db`, `empresa_{id}_sucursal_{id}_db`) y el flujo recomendado de provisión de datos y permisos.
