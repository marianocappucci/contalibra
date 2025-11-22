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
                        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
                    ]);
                    $pdo->exec("CREATE DATABASE IF NOT EXISTS `$dbName` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci");
                    $mensaje = "Base de datos '$dbName' creada/lista para usar.";
                } catch (Exception $e) {
                    $error = 'No se pudo crear la base: ' . $e->getMessage();
                }
            }
        }

        include __DIR__ . '/../vistas/superusuario/crear_bd.php';
    }
}
