# contalibra
Sistema Contable</br>
- Version de prueba aun no en producción -

## Restaurar base de datos
Si ves errores como `Table 'contadb.proveedores' doesn't exist` o `Table 'contadb.logs' doesn't exist`, levanta la base de datos inicial ejecutando:

```bash
php scripts/setup_database.php
```

El script crea la base `contadb` (si no existe) y carga el esquema/demo desde `backup_temp.sql`.
