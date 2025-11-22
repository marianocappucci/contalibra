<?php
require_once "libs/log_helper.php";
class MetodoPagoController {
    private $model;

    public function __construct(){
        registrarLog("Acceso a __construct","MetodoPago");
        $this->model = new MetodoPago();
    }

    public function index(){
        registrarLog("Acceso a index","MetodoPago");
        $metodos = $this->model->getAll();
        include __DIR__ . '/../vistas/metodos_pago/index.php';
    }

    public function crear(){
        registrarLog("Acceso a crear","MetodoPago");
        $metodo = null;
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->create($_POST);
            header('Location: index.php?controller=MetodoPago&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/metodos_pago/form.php';
    }

    public function editar(){
        registrarLog("Acceso a editar","MetodoPago");
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $metodo = $this->model->getById($id);
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update($id, $_POST);
            header('Location: index.php?controller=MetodoPago&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/metodos_pago/form.php';
    }

    public function eliminar(){
        registrarLog("Acceso a eliminar","MetodoPago");
        $id = $_GET['id'] ?? null;
        if ($id) {
            $this->model->delete($id);
        }
        header('Location: index.php?controller=MetodoPago&action=index');
        exit;
    }
}
