<?php
class Reporte {

    private $con;

    public function __construct() {
        $this->con = new mysqli("localhost", "root", "", "contadb");
        $this->con->set_charset("utf8");
    }

    // OBTENER TODAS LAS VENTAS
    public function getVentas() {
        $sql = "SELECT v.id, v.fecha, v.total, 
                       u.nombre AS usuario
                FROM ventas v
                LEFT JOIN usuarios u ON u.id = v.usuario_id
                ORDER BY v.fecha DESC";

        return $this->con->query($sql);
    }

}
?>
