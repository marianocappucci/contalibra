<?php
require_once __DIR__ . '/../config/config.php';

$options = [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::MYSQL_ATTR_MULTI_STATEMENTS => true,
];

$cliOptions = getopt('', ['empresa:', 'base:', 'master-user:', 'master-pass:', 'rol:']);

if (
    !isset($cliOptions['empresa'], $cliOptions['base'], $cliOptions['master-user'], $cliOptions['master-pass'], $cliOptions['rol'])
) {
    echo "Uso: php scripts/setup_database.php --empresa=<nombre> --base=<dbname> --master-user=<usuario> --master-pass=<password> --rol=<rol>\n";
    exit(1);
}

$empresa = trim($cliOptions['empresa']);
$dbName = sanitizeDbName($cliOptions['base']);
$masterUser = trim($cliOptions['master-user']);
$masterPass = $cliOptions['master-pass'];
$roleInput = trim($cliOptions['rol']);

try {
    $pdo = new PDO('mysql:host=' . DB_HOST . ';charset=utf8mb4', DB_USER, DB_PASS, $options);

    $pdo->exec("CREATE DATABASE IF NOT EXISTS `{$dbName}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;");
    echo "Base de datos '{$dbName}' verificada/creada.\n";

    $pdo = new PDO('mysql:host=' . DB_HOST . ';dbname=' . $dbName . ';charset=utf8mb4', DB_USER, DB_PASS, $options);

    restoreSchema($pdo);

    $roleId = resolveRoleId($pdo, $roleInput);
    $insertedUserId = createMasterUser($pdo, $masterUser, $masterPass, $roleId, $dbName);

    registerCompanyDatabase($pdo, $empresa, $dbName);

    echo "Base '{$dbName}' lista. Usuario maestro '{$masterUser}' configurado (ID {$insertedUserId}) con rol '{$roleInput}'.\n";
} catch (PDOException $e) {
    echo "Error de conexión/SQL: " . $e->getMessage() . "\n";
    exit(1);
} catch (RuntimeException $e) {
    echo $e->getMessage() . "\n";
    exit(1);
}

function sanitizeDbName(string $name): string
{
    $name = trim($name);
    if ($name === '' || !preg_match('/^[A-Za-z0-9_]+$/', $name)) {
        throw new RuntimeException('Nombre de base inválido. Use solo letras, números o guiones bajos.');
    }

    return $name;
}

function restoreSchema(PDO $pdo): void
{
    $sqlFile = __DIR__ . '/../backup_temp.sql';
    if (!file_exists($sqlFile)) {
        throw new RuntimeException('No se encontró el archivo SQL: ' . $sqlFile);
    }

    $sql = file_get_contents($sqlFile);
    $statements = array_filter(array_map('trim', explode(";\n", $sql)));

    foreach ($statements as $statement) {
        if (preg_match('/^INSERT\s+INTO\s+`?usuarios`?/i', $statement)) {
            continue;
        }

        $pdo->exec($statement);
    }

    echo "Esquema restaurado correctamente desde backup_temp.sql (sin usuarios).\n";
}

function resolveRoleId(PDO $pdo, string $roleInput): int
{
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

function createMasterUser(PDO $pdo, string $username, string $password, int $roleId, string $dbName): int
{
    if ($username === '' || $password === '') {
        throw new RuntimeException('Usuario y contraseña maestro son obligatorios.');
    }

    $stmt = $pdo->prepare('INSERT INTO usuarios (nombre, username, password, rol_id, activo, base_datos) VALUES (?, ?, ?, ?, 1, ?)');
    $stmt->execute([
        $username,
        $username,
        password_hash($password, PASSWORD_BCRYPT),
        $roleId,
        $dbName,
    ]);

    return (int) $pdo->lastInsertId();
}

function registerCompanyDatabase(PDO $pdo, string $empresa, string $dbName): void
{
    $tablesToCheck = ['empresas', 'tenants'];
    foreach ($tablesToCheck as $table) {
        if (!tableExists($pdo, $table)) {
            continue;
        }

        $columns = getTableColumns($pdo, $table);
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

        $insert = $pdo->prepare(sprintf('INSERT INTO `%s` (`%s`, `%s`) VALUES (?, ?)', $table, $nameColumn, $dbColumn));
        $insert->execute([$empresa, $dbName]);
        echo "Registro de empresa -> base almacenado en tabla '{$table}'.\n";
        return;
    }

    echo "No se registró empresa -> base porque no se encontró tabla de empresas/tenants compatible.\n";
}

function tableExists(PDO $pdo, string $table): bool
{
    $stmt = $pdo->prepare('SHOW TABLES LIKE ?');
    $stmt->execute([$table]);
    return (bool) $stmt->fetchColumn();
}

function getTableColumns(PDO $pdo, string $table): array
{
    $stmt = $pdo->query(sprintf('SHOW COLUMNS FROM `%s`', $table));
    return array_column($stmt->fetchAll(), 'Field');
}
?>
