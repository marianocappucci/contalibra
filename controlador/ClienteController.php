<?php
require_once "libs/log_helper.php";
class ClienteController {
    private $model;

    public function __construct(){
        registrarLog("Acceso a __construct","Cliente");
        $this->model = new Cliente();
    }

    public function index(){
        registrarLog("Acceso a index","Cliente");
        $clientes = $this->model->getAll();
        include __DIR__ . '/../vistas/clientes/index.php';
    }

    public function crear(){
        registrarLog("Acceso a crear","Cliente");
        $cliente = null;
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->create($_POST);
            header('Location: index.php?controller=Cliente&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/clientes/form.php';
    }

    public function editar(){
        registrarLog("Acceso a editar","Cliente");
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $cliente = $this->model->getById($id);
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update($id, $_POST);
            header('Location: index.php?controller=Cliente&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/clientes/form.php';
    }

    public function eliminar(){
        registrarLog("Acceso a eliminar","Cliente");
        $id = $_GET['id'] ?? null;
        if ($id) {
            $this->model->delete($id);
        }
        header('Location: index.php?controller=Cliente&action=index');
        exit;
    }
}
