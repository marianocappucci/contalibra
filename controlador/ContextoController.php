<?php
require_once "libs/log_helper.php";
require_once __DIR__ . '/../libs/TenantContext.php';
require_once __DIR__ . '/../config/database.php';

class ContextoController
{
    public function seleccionar()
    {
        if (!isset($_SESSION['user'])) {
            header('Location: index.php?controller=Auth&action=login');
            exit;
        }

        $empresaId = $_SESSION['empresa_id'] ?? ($_SESSION['user']['empresa_id'] ?? null);
        $empresaNombre = $_SESSION['empresa_nombre'] ?? '';

        $empresaModel = new Empresa();

        if (!$empresaId && isset($_SESSION['user']['base_datos'])) {
            $empresaResuelta = $empresaModel->getByBaseDatos($_SESSION['user']['base_datos']);

            if ($empresaResuelta) {
                $empresaId = (int) $empresaResuelta['id'];
                $_SESSION['empresa_id'] = $empresaId;
                $_SESSION['empresa_nombre'] = $empresaResuelta['nombre'];
                $empresaNombre = $empresaResuelta['nombre'];
            }
        }

        $empresa = $empresaId ? $empresaModel->getByIdFromDefault((int) $empresaId) : null;

        if (!$empresa) {
            $error = 'No se pudo identificar la empresa del usuario.';
            require __DIR__ . '/../vistas/auth/login.php';
            return;
        }

        $empresaDbName = $empresa['base_datos'] ?: TenantContext::databaseNameForEmpresa((int) $empresa['id']);
        $_SESSION['empresa_base'] = $empresaDbName;

        // Asegurar que la conexión activa apunte a la base de datos de la empresa
        // antes de consultar sus sucursales, evitando quedarse con una base previa
        // de otro tenant almacenada en la sesión.
        Database::setActiveDatabase($empresaDbName);

        // Renovar el modelo para que use la conexión activa (tenant) y no la
        // conexión previa al cambio de base de datos, que seguiría apuntando a
        // otra empresa.
        $empresaModel = new Empresa();

        $sucursales = $empresaModel->sucursalesConPuntosVenta((int) $empresa['id']);
        $error = null;

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $sucursalId = isset($_POST['sucursal_id']) ? (int) $_POST['sucursal_id'] : 0;
            $puntoVentaId = isset($_POST['punto_venta_id']) ? (int) $_POST['punto_venta_id'] : 0;

            $sucursalSeleccionada = $this->findSucursal($sucursales, $sucursalId);

            if (!$sucursalSeleccionada) {
                $error = 'Selecciona una sucursal válida.';
            }

            $puntoVentaSeleccionado = $sucursalSeleccionada
                ? $this->findPuntoVenta($sucursalSeleccionada['puntos_venta'], $puntoVentaId)
                : null;

            if (!$error && !$puntoVentaSeleccionado) {
                $error = 'Selecciona un punto de venta válido para la sucursal elegida.';
            }

            if (!$error) {
                $_SESSION['empresa_id'] = (int) $empresa['id'];
                $_SESSION['empresa_nombre'] = $empresaNombre ?: $empresa['nombre'];
                $_SESSION['empresa_base'] = $empresaDbName;
                $_SESSION['sucursal_id'] = $sucursalSeleccionada['id'];
                $_SESSION['sucursal_nombre'] = $sucursalSeleccionada['nombre'];
                $_SESSION['punto_venta_id'] = $puntoVentaSeleccionado['id'];
                $_SESSION['punto_venta_nombre'] = $puntoVentaSeleccionado['nombre'];

                TenantContext::setContext((int) $empresa['id'], (int) $sucursalSeleccionada['id']);
                $sucursalDbName = TenantContext::databaseNameForSucursalFromBase($empresaDbName, (int) $sucursalSeleccionada['id']);
                Database::setActiveDatabase($sucursalDbName);

                registrarLog('Selección de sucursal y punto de venta', 'Contexto');

                header('Location: index.php?controller=Dashboard&action=index');
                exit;
            }
        }

        require __DIR__ . '/../vistas/contexto/seleccionar.php';
    }

    private function findSucursal(array $sucursales, int $sucursalId): ?array
    {
        foreach ($sucursales as $sucursal) {
            if ((int) $sucursal['id'] === $sucursalId) {
                return $sucursal;
            }
        }

        return null;
    }

    private function findPuntoVenta(array $puntosVenta, int $puntoVentaId): ?array
    {
        foreach ($puntosVenta as $puntoVenta) {
            if ((int) $puntoVenta['id'] === $puntoVentaId) {
                return $puntoVenta;
            }
        }

        return null;
    }
}
