<?php
require_once "libs/log_helper.php";

class PuntoVentaController
{
    private $model;
    private $sucursalModel;

    public function __construct()
    {
        registrarLog("Acceso a __construct","PuntoVenta");
        $this->model = new PuntoVenta();
        $this->sucursalModel = new Sucursal();
    }

    public function index()
    {
        registrarLog("Acceso a index","PuntoVenta");
        $puntosVenta = $this->model->getAll();
        include __DIR__ . '/../vistas/puntos_venta/index.php';
    }

    public function crear()
    {
        registrarLog("Acceso a crear","PuntoVenta");
        $puntoVenta = null;
        $sucursales = $this->sucursalModel->getAll();

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->create($_POST);
            header('Location: index.php?controller=PuntoVenta&action=index');
            exit;
        }

        include __DIR__ . '/../vistas/puntos_venta/form.php';
    }

    public function editar()
    {
        registrarLog("Acceso a editar","PuntoVenta");
        $id = $_GET['id'] ?? null;

        if (!$id) {
            die('ID inválido');
        }

        $puntoVenta = $this->model->getById((int) $id);
        $sucursales = $this->sucursalModel->getAll();

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update((int) $id, $_POST);
            header('Location: index.php?controller=PuntoVenta&action=index');
            exit;
        }

        include __DIR__ . '/../vistas/puntos_venta/form.php';
    }

    public function eliminar()
    {
        registrarLog("Acceso a eliminar","PuntoVenta");
        $id = $_GET['id'] ?? null;

        if ($id) {
            $this->model->delete((int) $id);
        }

        header('Location: index.php?controller=PuntoVenta&action=index');
        exit;
    }
}
