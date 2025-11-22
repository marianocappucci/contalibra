<?php
require_once "libs/log_helper.php";
class SucursalController {
    private $model;

    public function __construct(){
        registrarLog("Acceso a __construct","Sucursal");
        $this->model = new Sucursal();
    }

    public function index(){
        registrarLog("Acceso a index","Sucursal");
        $sucursales = $this->model->getAll();
        include __DIR__ . '/../vistas/sucursales/index.php';
    }

    public function crear(){
        registrarLog("Acceso a crear","Sucursal");
        $sucursal = null;
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->create($_POST);
            header('Location: index.php?controller=Sucursal&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/sucursales/form.php';
    }

    public function editar(){
        registrarLog("Acceso a editar","Sucursal");
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $sucursal = $this->model->getById($id);
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update($id, $_POST);
            header('Location: index.php?controller=Sucursal&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/sucursales/form.php';
    }

    public function eliminar(){
        registrarLog("Acceso a eliminar","Sucursal");
        $id = $_GET['id'] ?? null;
        if ($id) {
            $this->model->delete($id);
        }
        header('Location: index.php?controller=Sucursal&action=index');
        exit;
    }
}
