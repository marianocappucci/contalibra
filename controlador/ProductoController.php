<?php
require_once "libs/log_helper.php";
class ProductoController {

    private $model;
    private $listaModel;
    private $proveedorModel;
    private $depositoModel;

    public function __construct(){
    registrarLog("Acceso a __construct","Producto");
        $this->model = new Producto();
        $this->listaModel = new ListaPrecio();
        $this->proveedorModel = new Proveedor();
        $this->depositoModel = new Deposito();
    }

    public function index(){
    registrarLog("Acceso a index","Producto");
        $productos = $this->model->getAll();
        include __DIR__ . '/../vistas/productos/index.php';
    }

public function buscarAjax(){
    registrarLog("Acceso a buscarAjax","Producto");
    $term = $_GET['term'] ?? '';
    $model = new Producto();
    $productos = $model->buscarPorNombre($term);

    header('Content-Type: application/json');
    echo json_encode($productos);
}


    public function crear(){
    registrarLog("Acceso a crear","Producto");
        $listas = $this->listaModel->getAll();
        $proveedores = $this->proveedorModel->getAll();
        $depositos = $this->depositoModel->getAll();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->create($_POST);
            header('Location: index.php?controller=Producto&action=index');
            exit;
        }
        $producto = null;
        include __DIR__ . '/../vistas/productos/form.php';
    }

    public function editar(){
    registrarLog("Acceso a editar","Producto");
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $listas = $this->listaModel->getAll();
        $proveedores = $this->proveedorModel->getAll();
        $depositos = $this->depositoModel->getAll();
        $producto = $this->model->getById($id);
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update($id, $_POST);
            header('Location: index.php?controller=Producto&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/productos/form.php';
    }

    public function eliminar(){
    registrarLog("Acceso a eliminar","Producto");
        $id = $_GET['id'] ?? null;
        if ($id) {
            $this->model->delete($id);
        }
        header('Location: index.php?controller=Producto&action=index');
        exit;
    }
}
