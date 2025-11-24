<?php
require_once "libs/log_helper.php";
class CajaController {

    private $model;
    private $usuarioModel;

    public function __construct($cajaModel = null, $usuarioModel = null){
    registrarLog("Acceso a __construct","Caja");
        $this->model = $cajaModel ?? new Caja();
        $this->usuarioModel = $usuarioModel ?? new Usuario();
    }

    public function index(){
    registrarLog("Acceso a index","Caja");
        $cajas = $this->model->getAll();
        include __DIR__ . '/../vistas/cajas/index.php';
    }

    public function abrir(){
    registrarLog("Acceso a abrir","Caja");
        $error = null;

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $resultado = $this->procesarApertura($_POST);

            if ($resultado['ok'] === true) {
                header('Location: index.php?controller=Caja&action=index');
                exit;
            }

            $error = $resultado['error'] ?? 'No se pudo abrir la caja.';
        }
        include __DIR__ . '/../vistas/cajas/abrir.php';
    }

    public function procesarApertura(array $payload): array
    {
        $usuario = $this->obtenerUsuarioDesdeSesion();

        if (!$usuario) {
            return [
                'ok' => false,
                'error' => 'Usuario no autenticado o inexistente en la base maestra. No se pudo abrir la caja.'
            ];
        }

        try {
            $data = [
                'nombre' => $payload['nombre'] ?? '',
                'saldo_inicial' => $payload['saldo_inicial'] ?? 0,
                'usuario_id' => $usuario['id']
            ];

            $this->model->abrirCaja($data);

            return ['ok' => true];
        } catch (PDOException $e) {
            return [
                'ok' => false,
                'error' => 'No se pudo abrir la caja en la base del cliente. Detalle: ' . $e->getMessage(),
            ];
        }
    }

    private function obtenerUsuarioDesdeSesion(): ?array
    {
        $usuarioId = $_SESSION['user']['id'] ?? null;

        if (!$usuarioId) {
            return null;
        }

        return $this->usuarioModel->getByIdFromDefault((int) $usuarioId) ?: null;
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
