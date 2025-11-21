<?php
class ReporteController {

    private $ventaModel;

    public function __construct() {
        $this->ventaModel = new Venta();
    }

    public function ventas() {
        $desde = $_GET['desde'] ?? null;
        $hasta = $_GET['hasta'] ?? null;
        $ventas = $this->ventaModel->listarVentas($desde, $hasta);
        include __DIR__ . '/../vistas/reportes/ventas.php';
    }
}
