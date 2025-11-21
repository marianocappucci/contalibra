<?php
require_once "libs/log_helper.php";
require_once "modelo/Reporte.php";

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
    public function exportarVentas() {

    $reporte = new Reporte();
    $ventas = $reporte->getVentas();

    header("Content-Type: application/vnd.ms-excel");
    header("Content-Disposition: attachment; filename=ventas.xls");
    header("Pragma: no-cache");
    header("Expires: 0");

    echo "<table border='1'>";
    echo "<tr>
            <th>ID</th>
            <th>Fecha</th>
            <th>Usuario</th>
            <th>Total</th>
          </tr>";

    while ($v = $ventas->fetch_assoc()) {
        echo "<tr>";
        echo "<td>".$v['id']."</td>";
        echo "<td>".$v['fecha']."</td>";
        echo "<td>".$v['usuario']."</td>";
        echo "<td>".$v['total']."</td>";
        echo "</tr>";
    }

    echo "</table>";
}


}
