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
$contextSelected = $isAuthenticated && isset($_SESSION['empresa_id'], $_SESSION['sucursal_id'], $_SESSION['punto_venta_id']);
$defaultController = $isAuthenticated
    ? ($contextSelected ? 'DashboardController' : 'ContextoController')
    : 'AuthController';
$defaultAction = $isAuthenticated
    ? ($contextSelected ? 'index' : 'seleccionar')
    : 'login';
$controllerName = isset($_GET['controller']) ? $_GET['controller'] . 'Controller' : $defaultController;
$action = isset($_GET['action']) ? $_GET['action'] : $defaultAction;

// Si no está logueado y no está en Auth, redirige a login
if (!$isAuthenticated && $controllerName !== 'AuthController') {
    header('Location: index.php?controller=Auth&action=login');
    exit;
}

// Si ya está autenticado y vuelve al login, enviarlo al dashboard
if ($isAuthenticated && $controllerName === 'AuthController' && $action === 'login') {
    $destinationController = $contextSelected ? 'Dashboard' : 'Contexto';
    $destinationAction = $contextSelected ? 'index' : 'seleccionar';
    header("Location: index.php?controller={$destinationController}&action={$destinationAction}");
    exit;
}

// Si está autenticado pero no ha elegido sucursal y punto de venta, forzar ese paso
if ($isAuthenticated && !$contextSelected && $controllerName !== 'ContextoController' && !($controllerName === 'AuthController' && $action === 'logout')) {
    header('Location: index.php?controller=Contexto&action=seleccionar');
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
