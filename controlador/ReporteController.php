<?php
require_once "libs/log_helper.php";
class ReporteController {

    private $ventaModel;

    public function __construct(){
    registrarLog("Acceso a __construct","Reporte");
        $this->ventaModel = new Venta();
    }

    public function ventas(){
    registrarLog("Acceso a ventas","Reporte");
        $desde = $_GET['desde'] ?? null;
        $hasta = $_GET['hasta'] ?? null;
        $ventas = $this->ventaModel->listarVentas($desde, $hasta);
        include __DIR__ . '/../vistas/reportes/ventas.php';
    }
}
