<?php
require_once "libs/log_helper.php";
class DashboardController {
    public function index(){
        registrarLog("Acceso a index","Dashboard");

        $configuracion = null;
        $empresaActiva = null;
        $baseActiva = $_SESSION['db_name'] ?? ($_SESSION['user']['base_datos'] ?? null);

        try {
            $configuracionModel = new Configuracion();
            $configuracion = $configuracionModel->get();
            $empresaActiva = $configuracion['nombre_fantasia'] ?? null;
        } catch (Exception $e) {
            // Si no podemos leer la configuración, usamos el nombre de la base como fallback
            $empresaActiva = $baseActiva;
        }

        if ($empresaActiva === null) {
            $empresaActiva = $baseActiva;
        }

        include __DIR__ . '/../vistas/dashboard/index.php';
    }
}
