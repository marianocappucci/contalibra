<?php
require_once __DIR__ . '/../config/config.php';

$options = [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::MYSQL_ATTR_MULTI_STATEMENTS => true,
];

try {
    // Conexión inicial sin base de datos para poder crearla si no existe
    $pdo = new PDO('mysql:host=' . DB_HOST . ';charset=utf8mb4', DB_USER, DB_PASS, $options);

    // Crear base de datos si no existe
    $pdo->exec("CREATE DATABASE IF NOT EXISTS `" . DB_NAME . "` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;");
    echo "Base de datos '" . DB_NAME . "' verificada/creada.\n";

    // Conectarse a la base recién creada
    $pdo = new PDO('mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4', DB_USER, DB_PASS, $options);

    $sqlFile = __DIR__ . '/../backup_temp.sql';
    if (!file_exists($sqlFile)) {
        throw new RuntimeException('No se encontró el archivo SQL: ' . $sqlFile);
    }

    $sql = file_get_contents($sqlFile);
    $statements = array_filter(array_map('trim', explode(";\n", $sql)));

    foreach ($statements as $statement) {
        $pdo->exec($statement);
    }

    echo "Esquema restaurado correctamente desde backup_temp.sql.\n";
} catch (PDOException $e) {
    echo "Error de conexión/SQL: " . $e->getMessage() . "\n";
    exit(1);
} catch (RuntimeException $e) {
    echo $e->getMessage() . "\n";
    exit(1);
}
?>
