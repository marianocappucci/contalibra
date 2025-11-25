<?php
/**
 * Gestiona el contexto de compañía/sucursal y las convenciones de nombres
 * para las bases de datos multitenant.
 */
class TenantContext
{
    /**
     * Define la compañía y sucursal activas en sesión.
     */
    public static function setContext(?int $empresaId, ?int $sucursalId = null): void
    {
        if ($empresaId === null) {
            self::clearContext();
            return;
        }

        $_SESSION['empresa_id'] = $empresaId;
        $_SESSION['sucursal_id'] = $sucursalId;
    }

    /**
     * Limpia el contexto guardado en sesión.
     */
    public static function clearContext(): void
    {
        unset($_SESSION['empresa_id'], $_SESSION['sucursal_id']);
    }

    public static function empresaId(): ?int
    {
        return isset($_SESSION['empresa_id']) ? (int) $_SESSION['empresa_id'] : null;
    }

    public static function sucursalId(): ?int
    {
        return isset($_SESSION['sucursal_id']) ? (int) $_SESSION['sucursal_id'] : null;
    }

    public static function databaseNameForEmpresa(int $empresaId): string
    {
        return sprintf('empresa_%d_db', $empresaId);
    }

    public static function databaseNameForSucursal(int $empresaId, int $sucursalId): string
    {
        return sprintf('empresa_%d_sucursal_%d_db', $empresaId, $sucursalId);
    }

    /**
     * Resuelve el nombre de la base activa respetando el contexto de la sesión
     * (sucursal > empresa > base explícita) y vuelve a la maestra si nada está configurado.
     */
    public static function activeDatabaseName(): string
    {
        if (!empty($_SESSION['db_name'])) {
            return (string) $_SESSION['db_name'];
        }

        $empresaId = self::empresaId();
        $sucursalId = self::sucursalId();

        if ($empresaId !== null && $sucursalId !== null) {
            return self::databaseNameForSucursal($empresaId, $sucursalId);
        }

        if ($empresaId !== null) {
            return self::databaseNameForEmpresa($empresaId);
        }

        return DB_NAME;
    }
}
