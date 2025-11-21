<?php
class ProductoController {

    private $model;
    private $listaModel;

    public function __construct() {
        $this->model = new Producto();
        $this->listaModel = new ListaPrecio();
    }

    public function index() {
        $productos = $this->model->getAll();
        include __DIR__ . '/../vistas/productos/index.php';
    }

public function buscarAjax() {
    $term = $_GET['term'] ?? '';
    $model = new Producto();
    $productos = $model->buscarPorNombre($term);

    header('Content-Type: application/json');
    echo json_encode($productos);
}


    public function crear() {
        $listas = $this->listaModel->getAll();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->create($_POST);
            header('Location: index.php?controller=Producto&action=index');
            exit;
        }
        $producto = null;
        include __DIR__ . '/../vistas/productos/form.php';
    }

    public function editar() {
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $listas = $this->listaModel->getAll();
        $producto = $this->model->getById($id);
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update($id, $_POST);
            header('Location: index.php?controller=Producto&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/productos/form.php';
    }

    public function eliminar() {
        $id = $_GET['id'] ?? null;
        if ($id) {
            $this->model->delete($id);
        }
        header('Location: index.php?controller=Producto&action=index');
        exit;
    }
}
