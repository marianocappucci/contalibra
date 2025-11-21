<?php
require_once "libs/log_helper.php";
class CajaController {

    private $model;

    public function __construct(){
    registrarLog("Acceso a __construct","Caja");
        $this->model = new Caja();
    }

    public function index(){
    registrarLog("Acceso a index","Caja");
        $cajas = $this->model->getAll();
        include __DIR__ . '/../vistas/cajas/index.php';
    }

    public function abrir(){
    registrarLog("Acceso a abrir","Caja");
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $data = [
                'nombre' => $_POST['nombre'],
                'saldo_inicial' => $_POST['saldo_inicial'],
                'usuario_id' => $_SESSION['user']['id']
            ];
            $this->model->abrirCaja($data);
            header('Location: index.php?controller=Caja&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/cajas/abrir.php';
    }

    public function cerrar(){
    registrarLog("Acceso a cerrar","Caja");
        $id = $_GET['id'] ?? null;
        if ($_SERVER['REQUEST_METHOD'] === 'POST' && $id) {
            $saldoFinal = $_POST['saldo_final'];
            $this->model->cerrarCaja($id, $_SESSION['user']['id'], $saldoFinal);
            header('Location: index.php?controller=Caja&action=index');
            exit;
        }
        include __DIR__ . '/../vistas/cajas/cerrar.php';
    }
}
