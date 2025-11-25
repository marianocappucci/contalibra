<?php
require_once "libs/log_helper.php";
class VentaController {

    private $ventaModel;
    private $productoModel;
    private $cajaModel;
    private $feModel;
    private $clienteModel;
    private $metodoPagoModel;
    private $sucursalModel;

    public function __construct(){
    registrarLog("Acceso a __construct","Venta");
        $this->ventaModel = new Venta();
        $this->productoModel = new Producto();
        $this->cajaModel = new Caja();
        $this->feModel = new FacturacionElectronica();
        $this->clienteModel = new Cliente();
        $this->metodoPagoModel = new MetodoPago();
        $this->sucursalModel = new Sucursal();
    }

    public function index(){
    registrarLog("Acceso a index","Venta");
        $ventas = $this->ventaModel->listarVentas();
        include __DIR__ . '/../vistas/ventas/lista.php';
    }

    public function nueva(){
    registrarLog("Acceso a nueva","Venta");
        $error = $_SESSION['venta_error'] ?? null;
        unset($_SESSION['venta_error']);

        $productos = $this->productoModel->getAll();
        $clientes = $this->clienteModel->getAll();
        $metodosPago = $this->metodoPagoModel->getAll();
        $sucursales = $this->sucursalModel->getAll();
        $caja = $this->cajaModel->getCajaAbiertaPorUsuario($_SESSION['user']['id']);
        if (!$caja) {
            $error = 'Debe abrir una caja antes de vender.';
        }
        include __DIR__ . '/../vistas/ventas/nueva.php';
    }

    public function registrar(){
    registrarLog("Acceso a registrar","Venta");
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            header('Location: index.php?controller=Venta&action=nueva');
            exit;
        }

        $caja = $this->cajaModel->getCajaAbiertaPorUsuario($_SESSION['user']['id']);
        if (!$caja) {
            $_SESSION['venta_error'] = 'Debe abrir una caja antes de registrar una venta.';
            header('Location: index.php?controller=Venta&action=nueva');
            exit;
        }

        $clienteId = $_POST['cliente_id'] ?? null;
        // Evitamos violar la FK cuando se factura a Consumidor Final
        if ($clienteId === '') {
            $clienteId = null;
        }

        if (!$clienteId && !empty($_POST['nuevo_cliente_nombre'])) {
            $clienteId = $this->clienteModel->create([
                'nombre' => $_POST['nuevo_cliente_nombre'],
                'tipo' => $_POST['nuevo_cliente_tipo'] ?? 'Consumidor Final',
                'documento' => $_POST['nuevo_cliente_documento'] ?? '',
                'saldo' => 0
            ]);
        }

        $items = [];
        $subtotal = 0;
        $itemsPost = $_POST['items'] ?? [];

        foreach ($itemsPost as $row) {
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

        if (!$items) {
            die('Debe agregar al menos un producto para guardar la venta.');
        }

        $iva = $subtotal * 0.21;
        $total = $subtotal + $iva;
        $metodoPagoId = $_POST['metodo_pago_id'] ?? null;
        $sucursalId = $_POST['sucursal_id'] ?? null;

        if ($metodoPagoId === '') {
            $metodoPagoId = null;
        }

        if ($sucursalId === '') {
            $sucursalId = null;
        }

        $dataVenta = [
            'caja_id' => $caja['id'],
            'usuario_id' => $_SESSION['user']['id'],
            'cliente_id' => $clienteId,
            'cliente' => $_POST['cliente'] ?? 'Consumidor Final',
            'subtotal' => $subtotal,
            'iva' => $iva,
            'total' => $total,
            'tipo_comprobante' => $_POST['tipo_comprobante'] ?? 'FA',
            'metodo_pago_id' => $metodoPagoId,
            'sucursal_id' => $sucursalId
        ];

        $ventaId = $this->ventaModel->save($dataVenta, $items);
        $venta = $this->ventaModel->getById($ventaId);
        $respFE = $this->feModel->enviarAFiscal($venta);
        header('Location: index.php?controller=Venta&action=ver&id=' . $ventaId);
        exit;
    }

    public function ver(){
    registrarLog("Acceso a ver","Venta");
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $venta = $this->ventaModel->getById($id);
        include __DIR__ . '/../vistas/ventas/ver.php';
    }
}
