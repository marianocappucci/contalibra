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
// comentario para ver cambios en github
$isAuthenticated = isset($_SESSION['user']);
$defaultController = $isAuthenticated ? 'DashboardController' : 'AuthController';
$defaultAction = $isAuthenticated ? 'index' : 'login';
$controllerName = isset($_GET['controller']) ? $_GET['controller'] . 'Controller' : $defaultController;
$action = isset($_GET['action']) ? $_GET['action'] : $defaultAction;

// Si no está logueado y no está en Auth, redirige a login
if (!$isAuthenticated && $controllerName !== 'AuthController') {
    header('Location: index.php?controller=Auth&action=login');
    exit;
}

// Si ya está autenticado y vuelve al login, enviarlo al dashboard
if ($isAuthenticated && $controllerName === 'AuthController' && $action === 'login') {
    header('Location: index.php?controller=Dashboard&action=index');
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
