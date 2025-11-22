<?php
require_once "libs/log_helper.php";
class SuperusuarioController {
    public function crearBase(){
        registrarLog("Acceso a crearBase","Superusuario");
        if (!isset($_SESSION['user']) || $_SESSION['user']['rol_nombre'] !== 'Superusuario') {
            die('No autorizado');
        }

        $mensaje = null;
        $error = null;
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $dbName = preg_replace('/[^a-zA-Z0-9_]/', '', $_POST['nombre_bd'] ?? '');
            if (!$dbName) {
                $error = 'Debe indicar un nombre de base de datos válido.';
            } else {
                try {
                    $dsn = 'mysql:host=' . DB_HOST;
                    $pdo = new PDO($dsn, DB_USER, DB_PASS, [
                        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                        PDO::MYSQL_ATTR_MULTI_STATEMENTS => true,
                    ]);
                    $pdo->exec("CREATE DATABASE IF NOT EXISTS `$dbName` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci");

                    $pdoDb = new PDO($dsn . ';dbname=' . $dbName . ';charset=utf8mb4', DB_USER, DB_PASS, [
                        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                    ]);

                    $sqlFile = __DIR__ . '/../backup_temp.sql';
                    if (!file_exists($sqlFile)) {
                        throw new RuntimeException('No se encontró el archivo SQL: ' . $sqlFile);
                    }

                    $sql = file_get_contents($sqlFile);
                    $statements = array_filter(array_map('trim', explode(";\n", $sql)));

                    foreach ($statements as $statement) {
                        if ($statement === '') {
                            continue;
                        }

                        // Evitamos clonar usuarios de demo pero mantenemos datos base (roles, configuraciones mínimas, etc.).
                        if (preg_match('/^\s*INSERT\s+INTO\s+`?usuarios`?/i', $statement)) {
                            continue;
                        }

                        $pdoDb->exec($statement);
                    }

                    $mensaje = "Base de datos '$dbName' creada y estructura importada (sin usuarios de demo).";
                } catch (Exception $e) {
                    $error = 'No se pudo crear la base: ' . $e->getMessage();
                }
            }
        }

        include __DIR__ . '/../vistas/superusuario/crear_bd.php';
    }
}
