<?php
require_once __DIR__ . '/../config/config.php';

$options = getopt('', ['base::']);
$dbName = sanitizeDbName($options['base'] ?? DB_NAME);

$pdo = new PDO('mysql:host=' . DB_HOST . ';dbname=' . $dbName . ';charset=utf8mb4', DB_USER, DB_PASS, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
]);

echo "Aplicando migración de empresas a la base '{$dbName}'.\n";

ensureEmpresasTable($pdo, $dbName);
ensureUsuariosEmpresaRelation($pdo, $dbName);
ensureSucursalesEmpresaRelation($pdo, $dbName);

echo "Migración finalizada.\n";

function ensureEmpresasTable(PDO $pdo, string $dbName): void
{
    if (tableExists($pdo, $dbName, 'empresas')) {
        echo "- La tabla empresas ya existe.\n";
        return;
    }

    $pdo->exec(
        'CREATE TABLE `empresas` (
            `id` int(11) NOT NULL AUTO_INCREMENT,
            `nombre` varchar(150) NOT NULL,
            `base_datos` varchar(120) DEFAULT NULL,
            `creado_en` datetime NOT NULL,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uq_empresas_nombre` (`nombre`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;'
    );

    echo "- Tabla empresas creada.\n";
}

function ensureUsuariosEmpresaRelation(PDO $pdo, string $dbName): void
{
    if (!tableExists($pdo, $dbName, 'usuarios')) {
        echo "- La tabla usuarios no existe en {$dbName}; se omite su migración.\n";
        return;
    }

    if (!columnExists($pdo, $dbName, 'usuarios', 'empresa_id')) {
        $pdo->exec('ALTER TABLE `usuarios` ADD COLUMN `empresa_id` INT(11) DEFAULT NULL AFTER `rol_id`');
        echo "- Columna empresa_id agregada a usuarios.\n";
    } else {
        echo "- Columna empresa_id ya existía en usuarios.\n";
    }

    if (!indexExists($pdo, $dbName, 'usuarios', 'empresa_id')) {
        $pdo->exec('ALTER TABLE `usuarios` ADD INDEX (`empresa_id`)');
        echo "- Índice empresa_id agregado a usuarios.\n";
    }

    if (!tableExists($pdo, $dbName, 'empresas')) {
        echo "- No se creó la llave foránea de usuarios porque falta la tabla empresas.\n";
        return;
    }

    if (foreignKeyExists($pdo, $dbName, 'usuarios', 'usuarios_ibfk_empresas')) {
        echo "- La llave foránea usuarios_ibfk_empresas ya existía.\n";
        return;
    }

    $pdo->exec(
        'ALTER TABLE `usuarios` 
            ADD CONSTRAINT `usuarios_ibfk_empresas` FOREIGN KEY (`empresa_id`) REFERENCES `empresas`(`id`) ON DELETE SET NULL'
    );
    echo "- Llave foránea usuarios_ibfk_empresas creada.\n";
}

function ensureSucursalesEmpresaRelation(PDO $pdo, string $dbName): void
{
    if (!tableExists($pdo, $dbName, 'sucursales')) {
        echo "- La tabla sucursales no existe en {$dbName}; se omite su migración.\n";
        return;
    }

    if (!columnExists($pdo, $dbName, 'sucursales', 'empresa_id')) {
        $pdo->exec('ALTER TABLE `sucursales` ADD COLUMN `empresa_id` INT(11) DEFAULT NULL AFTER `ciudad`');
        echo "- Columna empresa_id agregada a sucursales.\n";
    } else {
        echo "- Columna empresa_id ya existía en sucursales.\n";
    }

    if (!indexExists($pdo, $dbName, 'sucursales', 'empresa_id')) {
        $pdo->exec('ALTER TABLE `sucursales` ADD INDEX (`empresa_id`)');
        echo "- Índice empresa_id agregado a sucursales.\n";
    }

    if (!tableExists($pdo, $dbName, 'empresas')) {
        echo "- No se creó la llave foránea de sucursales porque falta la tabla empresas.\n";
        return;
    }

    $existingFkNames = ['sucursales_ibfk_1', 'sucursales_ibfk_empresas'];
    foreach ($existingFkNames as $fkName) {
        if (foreignKeyExists($pdo, $dbName, 'sucursales', $fkName)) {
            echo "- La llave foránea {$fkName} ya existía en sucursales.\n";
            return;
        }
    }

    $pdo->exec(
        'ALTER TABLE `sucursales` 
            ADD CONSTRAINT `sucursales_ibfk_empresas` FOREIGN KEY (`empresa_id`) REFERENCES `empresas`(`id`) ON DELETE SET NULL'
    );
    echo "- Llave foránea sucursales_ibfk_empresas creada.\n";
}

function sanitizeDbName(string $name): string
{
    $name = trim($name);
    if ($name === '') {
        throw new RuntimeException('El nombre de la base no puede estar vacío.');
    }

    if (!preg_match('/^[A-Za-z0-9_]+$/', $name)) {
        throw new RuntimeException('Nombre de base inválido. Usa solo letras, números o guiones bajos.');
    }

    return $name;
}

function tableExists(PDO $pdo, string $dbName, string $table): bool
{
    $stmt = $pdo->prepare(
        'SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?'
    );
    $stmt->execute([$dbName, $table]);

    return (bool) $stmt->fetchColumn();
}

function columnExists(PDO $pdo, string $dbName, string $table, string $column): bool
{
    $stmt = $pdo->prepare(
        'SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?'
    );
    $stmt->execute([$dbName, $table, $column]);

    return (bool) $stmt->fetchColumn();
}

function indexExists(PDO $pdo, string $dbName, string $table, string $indexName): bool
{
    $stmt = $pdo->prepare(
        'SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND INDEX_NAME = ?'
    );
    $stmt->execute([$dbName, $table, $indexName]);

    return (bool) $stmt->fetchColumn();
}

function foreignKeyExists(PDO $pdo, string $dbName, string $table, string $fkName): bool
{
    $stmt = $pdo->prepare(
        'SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND CONSTRAINT_NAME = ? AND CONSTRAINT_TYPE = "FOREIGN KEY"'
    );
    $stmt->execute([$dbName, $table, $fkName]);

    return (bool) $stmt->fetchColumn();
}
