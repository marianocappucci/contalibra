<?php
class CajaController {

    private $model;

    public function __construct() {
        $this->model = new Caja();
    }

    public function index() {
        $cajas = $this->model->getAll();
        include __DIR__ . '/../vistas/cajas/index.php';
    }

    public function abrir() {
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

    public function cerrar() {
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
