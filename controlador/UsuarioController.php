<?php
require_once "libs/log_helper.php";
class UsuarioController {

    private $model;

    public function __construct(){
    registrarLog("Acceso a __construct","Usuario");
        $this->model = new Usuario();
    }

    public function index(){
    registrarLog("Acceso a index","Usuario");
        $usuarios = $this->model->getAll();
        include __DIR__ . '/../vistas/usuarios/index.php';
    }

    public function crear(){
    registrarLog("Acceso a crear","Usuario");
        $roles = $this->model->getRoles();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->create($_POST);
            header('Location: index.php?controller=Usuario&action=index');
            exit;
        }
        $usuario = null;
        include __DIR__ . '/../vistas/usuarios/form.php';
    }

    public function editar(){
    registrarLog("Acceso a editar","Usuario");
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

    public function eliminar(){
    registrarLog("Acceso a eliminar","Usuario");
        $id = $_GET['id'] ?? null;
        if ($id) {
            $this->model->delete($id);
        }
        header('Location: index.php?controller=Usuario&action=index');
        exit;
    }
}
