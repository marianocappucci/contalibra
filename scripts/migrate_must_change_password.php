<?php
require_once __DIR__ . '/../config/config.php';

$options = getopt('', ['base::']);
$dbName = sanitizeDbName($options['base'] ?? DB_NAME);

$pdo = new PDO('mysql:host=' . DB_HOST . ';dbname=' . $dbName . ';charset=utf8mb4', DB_USER, DB_PASS, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
]);

echo "Aplicando migración must_change_password en la base '{$dbName}'.\n";

if (!tableExists($pdo, $dbName, 'usuarios')) {
    echo "- La tabla usuarios no existe en {$dbName}; no se realizaron cambios.\n";
    exit(0);
}

if (columnExists($pdo, $dbName, 'usuarios', 'must_change_password')) {
    echo "- La columna must_change_password ya existe; nada que hacer.\n";
    exit(0);
}

$pdo->exec('ALTER TABLE `usuarios` ADD COLUMN `must_change_password` TINYINT(1) NOT NULL DEFAULT 0 AFTER `base_datos`');
$pdo->exec('UPDATE `usuarios` SET `must_change_password` = 0 WHERE `must_change_password` IS NULL');

echo "- Columna must_change_password creada y valores inicializados en usuarios.\n";
echo "Migración completada.\n";

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
?>
