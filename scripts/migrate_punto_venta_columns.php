<?php
require_once __DIR__ . '/../config/config.php';

$options = getopt('', ['base::']);
$dbName = sanitizeDbName($options['base'] ?? DB_NAME);

$pdo = new PDO('mysql:host=' . DB_HOST . ';dbname=' . $dbName . ';charset=utf8mb4', DB_USER, DB_PASS, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
]);

echo "Aplicando migración a la base '{$dbName}'.\n";
ensurePuntoVentaSupport($pdo, $dbName, 'cajas', 'estado', 'cajas_ibfk_3');
ensurePuntoVentaSupport($pdo, $dbName, 'ventas', 'sucursal_id', 'ventas_ibfk_6');

echo "Migración completada.\n";

function ensurePuntoVentaSupport(PDO $pdo, string $dbName, string $table, string $afterColumn, string $fkName): void
{
    if (!tableExists($pdo, $dbName, $table)) {
        echo "- La tabla {$table} no existe en {$dbName}; se omite.\n";
        return;
    }

    if (!columnExists($pdo, $dbName, $table, 'punto_venta_id')) {
        $pdo->exec(sprintf(
            'ALTER TABLE `%s` ADD COLUMN `punto_venta_id` INT(11) DEFAULT NULL AFTER `%s`',
            $table,
            $afterColumn
        ));
        echo "- Columna punto_venta_id creada en {$table}.\n";
    } else {
        echo "- Columna punto_venta_id ya existía en {$table}.\n";
    }

    if (!indexExists($pdo, $dbName, $table, 'punto_venta_id')) {
        $pdo->exec(sprintf('ALTER TABLE `%s` ADD INDEX (`punto_venta_id`)', $table));
        echo "- Índice punto_venta_id agregado a {$table}.\n";
    }

    if (foreignKeyExists($pdo, $dbName, $table, $fkName)) {
        echo "- La llave foránea {$fkName} ya existía en {$table}.\n";
        return;
    }

    if (!tableExists($pdo, $dbName, 'puntos_venta')) {
        echo "- No se pudo crear la llave foránea {$fkName} porque falta la tabla puntos_venta.\n";
        return;
    }

    $pdo->exec(sprintf(
        'ALTER TABLE `%s` ADD CONSTRAINT `%s` FOREIGN KEY (`punto_venta_id`) REFERENCES `puntos_venta`(`id`)',
        $table,
        $fkName
    ));
    echo "- Llave foránea {$fkName} creada en {$table}.\n";
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
