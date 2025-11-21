<?php
class VentaController {

    private $ventaModel;
    private $productoModel;
    private $cajaModel;
    private $feModel;

    public function __construct() {
        $this->ventaModel = new Venta();
        $this->productoModel = new Producto();
        $this->cajaModel = new Caja();
        $this->feModel = new FacturacionElectronica();
    }

    public function index() {
        $ventas = $this->ventaModel->listarVentas();
        include __DIR__ . '/../vistas/ventas/lista.php';
    }

    public function nueva() {
        $productos = $this->productoModel->getAll();
        $caja = $this->cajaModel->getCajaAbiertaPorUsuario($_SESSION['user']['id']);
        if (!$caja) {
            $error = 'Debe abrir una caja antes de vender.';
        }
        if ($_SERVER['REQUEST_METHOD'] === 'POST' && $caja) {
            $items = [];
            $subtotal = 0;
            foreach ($_POST['items'] as $row) {
                if (empty($row['producto_id']) || $row['cantidad'] <= 0) continue;
                $totalLinea = $row['cantidad'] * $row['precio_unitario'];
                $items[] = [
                    'producto_id' => $row['producto_id'],
                    'cantidad' => $row['cantidad'],
                    'precio_unitario' => $row['precio_unitario'],
                    'total' => $totalLinea
                ];
                $subtotal += $totalLinea;
            }
            $iva = $subtotal * 0.21;
            $total = $subtotal + $iva;
            $dataVenta = [
                'caja_id' => $caja['id'],
                'usuario_id' => $_SESSION['user']['id'],
                'cliente' => $_POST['cliente'] ?? 'Consumidor Final',
                'subtotal' => $subtotal,
                'iva' => $iva,
                'total' => $total,
                'tipo_comprobante' => $_POST['tipo_comprobante'] ?? 'FA'
            ];
            $ventaId = $this->ventaModel->crearVenta($dataVenta, $items);
            $venta = $this->ventaModel->getById($ventaId);
            $respFE = $this->feModel->enviarAFiscal($venta);
            header('Location: index.php?controller=Venta&action=ver&id=' . $ventaId);
            exit;
        }
        include __DIR__ . '/../vistas/ventas/nueva.php';
    }

    public function ver() {
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $venta = $this->ventaModel->getById($id);
        include __DIR__ . '/../vistas/ventas/ver.php';
    }
}
