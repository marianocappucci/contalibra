<?php
session_start();
require_once __DIR__ . '/config/config.php';
require_once __DIR__ . '/config/database.php';

// Autocarga muy simple de modelos y controladores
spl_autoload_register(function($class){
    $paths = ['modelo', 'controlador'];
    foreach ($paths as $p) {
        $file = __DIR__ . '/' . $p . '/' . $class . '.php';
        if (file_exists($file)) {
            require_once $file;
            return;
        }
    }
});
// este es un comentario que agregue para el github
$controllerName = isset($_GET['controller']) ? $_GET['controller'] . 'Controller' : 'AuthController';
$action = isset($_GET['action']) ? $_GET['action'] : 'login';

// Si no está logueado y no está en Auth, redirige a login
if (!isset($_SESSION['user']) && $controllerName !== 'AuthController') {
    header('Location: index.php?controller=Auth&action=login');
    exit;
}

$controllerFile = __DIR__ . '/controlador/' . $controllerName . '.php';
if (!file_exists($controllerFile)) {
    die('Controlador no encontrado');
}

$controller = new $controllerName();
if (!method_exists($controller, $action)) {
    die('Acción no válida');
}

$controller->$action();
