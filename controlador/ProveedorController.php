<?php
require_once "libs/log_helper.php";
class ProveedorController {
    private $model;

    public function __construct(){
        registrarLog("Acceso a __construct","Proveedor");
        $this->model = new Proveedor();
    }

    public function index(){
        registrarLog("Acceso a index","Proveedor");
        $proveedores = $this->model->getAll();
        include __DIR__ . '/../vistas/proveedores/index.php';
    }

    public function crear(){
        registrarLog("Acceso a crear","Proveedor");
        $proveedor = null;
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->create($_POST);
            header('Location: index.php?controller=Proveedor&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/proveedores/form.php';
    }

    public function editar(){
        registrarLog("Acceso a editar","Proveedor");
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $proveedor = $this->model->getById($id);
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update($id, $_POST);
            header('Location: index.php?controller=Proveedor&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/proveedores/form.php';
    }

    public function eliminar(){
        registrarLog("Acceso a eliminar","Proveedor");
        $id = $_GET['id'] ?? null;
        if ($id) {
            $this->model->delete($id);
        }
        header('Location: index.php?controller=Proveedor&action=index');
        exit;
    }
}
