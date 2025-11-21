<?php
class UsuarioController {

    private $model;

    public function __construct() {
        $this->model = new Usuario();
    }

    public function index() {
        $usuarios = $this->model->getAll();
        include __DIR__ . '/../vistas/usuarios/index.php';
    }

    public function crear() {
        $roles = $this->model->getRoles();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->create($_POST);
            header('Location: index.php?controller=Usuario&action=index');
            exit;
        }
        $usuario = null;
        include __DIR__ . '/../vistas/usuarios/form.php';
    }

    public function editar() {
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $roles = $this->model->getRoles();
        $usuario = $this->model->getById($id);
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update($id, $_POST);
            header('Location: index.php?controller=Usuario&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/usuarios/form.php';
    }

    public function eliminar() {
        $id = $_GET['id'] ?? null;
        if ($id) {
            $this->model->delete($id);
        }
        header('Location: index.php?controller=Usuario&action=index');
        exit;
    }
}
