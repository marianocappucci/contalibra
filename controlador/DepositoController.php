<?php
require_once "libs/log_helper.php";
class DepositoController {
    private $model;
    private $sucursalModel;

    public function __construct(){
        registrarLog("Acceso a __construct","Deposito");
        $this->model = new Deposito();
        $this->sucursalModel = new Sucursal();
    }

    public function index(){
        registrarLog("Acceso a index","Deposito");
        $depositos = $this->model->getAll();
        include __DIR__ . '/../vistas/depositos/index.php';
    }

    public function crear(){
        registrarLog("Acceso a crear","Deposito");
        $deposito = null;
        $sucursales = $this->sucursalModel->getAll();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->create($_POST);
            header('Location: index.php?controller=Deposito&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/depositos/form.php';
    }

    public function editar(){
        registrarLog("Acceso a editar","Deposito");
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $deposito = $this->model->getById($id);
        $sucursales = $this->sucursalModel->getAll();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update($id, $_POST);
            header('Location: index.php?controller=Deposito&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/depositos/form.php';
    }

    public function eliminar(){
        registrarLog("Acceso a eliminar","Deposito");
        $id = $_GET['id'] ?? null;
        if ($id) {
            $this->model->delete($id);
        }
        header('Location: index.php?controller=Deposito&action=index');
        exit;
    }
}
