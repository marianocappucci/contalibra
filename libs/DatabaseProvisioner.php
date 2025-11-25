<?php
class DatabaseProvisioner
{
    private const SCHEMA_FILE = __DIR__ . '/../backup_temp.sql';

    public static function sanitizeDbName(string $name): string
    {
        $name = trim($name);
        $name = preg_replace('/[^A-Za-z0-9_]+/', '_', $name);
        $name = trim($name, '_');

        if ($name === '') {
            throw new RuntimeException('El nombre de la base de datos no puede quedar vacío.');
        }

        return $name;
    }

    public static function generateCompanyDbName(string $empresaNombre): string
    {
        return 'contadb_' . self::sanitizeDbName(strtolower($empresaNombre));
    }

    public static function generateSucursalDbName(
        string $empresaBase,
        string $sucursalNombre,
        int $empresaId,
        int $sucursalId
    ): string {
        $base = $empresaBase !== ''
            ? self::sanitizeDbName(preg_replace('/_db$/', '', $empresaBase))
            : self::sanitizeDbName(TenantContext::databaseNameForEmpresa($empresaId));

        return self::sanitizeDbName(sprintf('%s_sucursal_%d_db', $base, $sucursalId));
    }

    public static function provisionDatabase(string $dbName): PDO
    {
        $options = [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::MYSQL_ATTR_MULTI_STATEMENTS => true,
        ];

        $pdoRoot = new PDO('mysql:host=' . DB_HOST . ';charset=utf8mb4', DB_USER, DB_PASS, $options);
        $pdoRoot->exec("CREATE DATABASE IF NOT EXISTS `{$dbName}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;");

        return new PDO('mysql:host=' . DB_HOST . ';dbname=' . $dbName . ';charset=utf8mb4', DB_USER, DB_PASS, $options);
    }

    public static function restoreSchema(PDO $pdo): void
    {
        if (!file_exists(self::SCHEMA_FILE)) {
            throw new RuntimeException('No se encontró el archivo SQL: ' . self::SCHEMA_FILE);
        }

        $sql = file_get_contents(self::SCHEMA_FILE);
        $statements = array_filter(array_map('trim', explode(";\n", $sql)));

        foreach ($statements as $statement) {
            if ($statement === '') {
                continue;
            }

            if (preg_match('/^\s*INSERT\s+INTO\s+`?usuarios`?/i', $statement)) {
                continue;
            }

            $pdo->exec($statement);
        }
    }

    public static function registerCompanyDatabase(PDO $pdo, string $empresaNombre, string $dbName): void
    {
        $tablesToCheck = ['empresas', 'tenants'];
        foreach ($tablesToCheck as $table) {
            if (!self::tableExists($pdo, $table)) {
                continue;
            }

            $columns = self::getTableColumns($pdo, $table);
            $nameColumn = null;
            foreach (['empresa', 'nombre'] as $candidate) {
                if (in_array($candidate, $columns, true)) {
                    $nameColumn = $candidate;
                    break;
                }
            }

            $dbColumn = null;
            foreach (['base_datos', 'database', 'db_name'] as $candidate) {
                if (in_array($candidate, $columns, true)) {
                    $dbColumn = $candidate;
                    break;
                }
            }

            if ($nameColumn === null || $dbColumn === null) {
                continue;
            }

            $rowCount = (int) $pdo->query(sprintf('SELECT COUNT(*) FROM `%s`', $table))->fetchColumn();
            if ($rowCount > 0) {
                continue;
            }

            $existing = $pdo->prepare(
                sprintf('SELECT COUNT(*) FROM `%s` WHERE `%s` = ? OR `%s` = ?', $table, $nameColumn, $dbColumn)
            );
            $existing->execute([$empresaNombre, $dbName]);

            if ((int) $existing->fetchColumn() > 0) {
                return;
            }

            $insert = $pdo->prepare(sprintf('INSERT INTO `%s` (`%s`, `%s`) VALUES (?, ?)', $table, $nameColumn, $dbColumn));
            $insert->execute([$empresaNombre, $dbName]);
            return;
        }
    }

    public static function resolveRoleId(PDO $pdo, string $roleInput): int
    {
        $roleInput = trim($roleInput);
        if ($roleInput === '') {
            throw new RuntimeException('El rol maestro no puede estar vacío.');
        }

        if (ctype_digit($roleInput)) {
            $stmt = $pdo->prepare('SELECT id FROM roles WHERE id = ? LIMIT 1');
            $stmt->execute([(int) $roleInput]);
            $result = $stmt->fetchColumn();
            if ($result !== false) {
                return (int) $result;
            }
        }

        $stmt = $pdo->prepare('SELECT id FROM roles WHERE nombre = ? LIMIT 1');
        $stmt->execute([$roleInput]);
        $roleId = $stmt->fetchColumn();
        if ($roleId !== false) {
            return (int) $roleId;
        }

        $insert = $pdo->prepare('INSERT INTO roles (nombre) VALUES (?)');
        $insert->execute([$roleInput]);

        return (int) $pdo->lastInsertId();
    }

    public static function createUser(
        PDO $pdo,
        string $username,
        string $password,
        int $roleId,
        string $dbName,
        ?int $empresaId = null,
        bool $mustChangePassword = false
    ): int
    {
        if ($username === '' || $password === '') {
            throw new RuntimeException('Usuario y contraseña maestro son obligatorios.');
        }

        $stmt = $pdo->prepare(
            'INSERT INTO usuarios (nombre, username, password, rol_id, activo, base_datos, empresa_id, must_change_password) '
            . 'VALUES (?, ?, ?, ?, 1, ?, ?, ?)'
        );
        $stmt->execute([
            $username,
            $username,
            password_hash($password, PASSWORD_BCRYPT),
            $roleId,
            $dbName,
            $empresaId,
            $mustChangePassword ? 1 : 0,
        ]);

        return (int) $pdo->lastInsertId();
    }

    private static function slugify(string $value): string
    {
        $value = strtolower(trim($value));
        $value = preg_replace('/[^a-z0-9_]+/i', '_', $value);

        return trim($value, '_');
    }

    private static function tableExists(PDO $pdo, string $table): bool
    {
        $stmt = $pdo->prepare('SHOW TABLES LIKE ?');
        $stmt->execute([$table]);
        return (bool) $stmt->fetchColumn();
    }

    private static function getTableColumns(PDO $pdo, string $table): array
    {
        $stmt = $pdo->query(sprintf('SHOW COLUMNS FROM `%s`', $table));
        return array_column($stmt->fetchAll(), 'Field');
    }
}
