<?php
class ConfiguracionController {

    private $model;

    public function __construct() {
        $this->model = new Configuracion();
        if (!isset($_SESSION['user']) || $_SESSION['user']['rol_nombre'] !== 'Administrador') {
            die("Acceso denegado");
        }
    }

    public function index() {
        $config = $this->model->get();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update($_POST);
            $config = $this->model->get();
            $mensaje = "Configuración actualizada correctamente";
        }
        include __DIR__ . '/../vistas/configuracion/index.php';
    }
}
