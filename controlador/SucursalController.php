<?php
require_once "libs/log_helper.php";
class SucursalController {
    private $model;
    private $empresaModel;

    public function __construct(){
        registrarLog("Acceso a __construct","Sucursal");
        $this->model = new Sucursal();
        $this->empresaModel = new Empresa();
    }

    public function index(){
        registrarLog("Acceso a index","Sucursal");
        $sucursales = $this->model->getAll();
        include __DIR__ . '/../vistas/sucursales/index.php';
    }

    public function crear(){
        registrarLog("Acceso a crear","Sucursal");
        $sucursal = null;
        $empresas = $this->empresaModel->getAll();
        $error = null;
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $data = $_POST;
            $empresaId = $data['empresa_id'] ?? '';
            $data['empresa_id'] = $empresaId === '' ? null : (int) $empresaId;
            try {
                $this->model->create($data);
                header('Location: index.php?controller=Sucursal&action=index');
                exit;
            } catch (Throwable $e) {
                $error = 'No se pudo crear la sucursal: ' . $e->getMessage();
                $sucursal = $data;
            }
        }
        include __DIR__ . '/../vistas/sucursales/form.php';
    }

    public function editar(){
        registrarLog("Acceso a editar","Sucursal");
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $sucursal = $this->model->getById($id);
        $empresas = $this->empresaModel->getAll();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $data = $_POST;
            $empresaId = $data['empresa_id'] ?? '';
            $data['empresa_id'] = $empresaId === '' ? null : (int) $empresaId;
            $this->model->update($id, $data);
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
