<?php
    $configuracion = null;
    $empresaActiva = null;
    $baseActiva = $_SESSION['db_name'] ?? ($_SESSION['user']['base_datos'] ?? null);

    try {
        $configuracionModel = new Configuracion();
        $configuracion = $configuracionModel->get();
        $empresaActiva = $configuracion['nombre_fantasia'] ?? null;
    } catch (Exception $e) {
        $empresaActiva = $baseActiva;
    }

    if ($empresaActiva === null) {
        $empresaActiva = $baseActiva;
    }

    $empresaActivaNombre = $empresaActiva ?? 'No configurada';
?>

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">

<style>
    #sidebar {
        width: 260px;
        height: 100vh;
        background: #1f1f1f;
        color: #f1f1f1;
        position: fixed;
        left: 0;
        top: 0;
        overflow-y: auto;
        padding: 16px 18px;
        border-right: 1px solid #2b2b2b;
        z-index: 1100;
        display: flex;
        flex-direction: column;
    }

    #sidebar .sidebar-title {
        font-size: 1.25rem;
        font-weight: 700;
        padding: 10px 12px;
        border-bottom: 1px solid #343434;
        display: flex;
        align-items: flex-start;
        gap: 10px;
        background: #252525;
        border-radius: 10px;
        margin-bottom: 12px;
        position: sticky;
        top: 0;
        z-index: 10;
    }

    #sidebar .sidebar-title i {
        font-size: 1.5rem;
        color: #ffc107;
    }

    #sidebar .sidebar-heading {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }

    #sidebar .sidebar-heading .sidebar-brand {
        line-height: 1.2;
    }

    #sidebar .sidebar-heading .sidebar-company {
        font-size: 0.85rem;
        color: #8f8f8fff;
    }

    #sidebar .nav {
        gap: 6px;
        display: flex;
        flex-direction: column;
        flex: 1;
    }

    #sidebar .nav-link,
    #sidebar .btn-toggle {
        color: #d7d7d7;
        padding: 10px 12px;
        border-radius: 10px;
        font-size: 0.95rem;
        display: flex;
        align-items: center;
        gap: 10px;
        text-decoration: none;
        transition: background 0.2s ease, color 0.2s ease;
    }

    #sidebar .nav-link:hover,
    #sidebar .btn-toggle:hover,
    #sidebar .btn-toggle:focus {
        background: #2f2f2f;
        color: #fff;
    }

    #sidebar .nav-link i,
    #sidebar .btn-toggle i {
        font-size: 1.1rem;
        color: #ffc107;
    }

    #sidebar .btn-toggle {
        width: 100%;
        background: transparent;
        border: none;
        text-align: left;
    }

    #sidebar .btn-toggle::after {
        content: '\25bc';
        margin-left: auto;
        font-size: 0.8rem;
        transition: transform 0.2s ease;
    }

    #sidebar .btn-toggle.collapsed::after {
        transform: rotate(-90deg);
    }

    #sidebar .btn-toggle-nav {
        padding-left: 32px;
    }

    #sidebar .btn-toggle-nav a {
        padding: 6px 0;
        color: #c9c9c9;
    }

    #sidebar .btn-toggle-nav a:hover {
        color: #fff;
    }

    #content {
        margin-left: 260px;
        padding: 20px;
        padding-top: 80px;
        transition: margin-left 0.3s ease;
    }

</style>

<div id="sidebar">
    <div class="sidebar-title">

        
        <div class="sidebar-heading">
            <span class="sidebar-brand">Contalibra</span>
            <small class="sidebar-company"><?php echo htmlspecialchars($empresaActivaNombre); ?></small>
        </div>

    </div>


    <nav class="nav flex-column">
        <a class="nav-link" href="index.php?controller=Dashboard&action=index">
            <i class="bi bi-house-door-fill"></i>
            <span>Principal</span>
        </a>

        <div class="nav-item">
            <button class="btn-toggle align-items-center rounded collapsed" data-bs-toggle="collapse" data-bs-target="#menuVentas" aria-expanded="false">
                <i class="bi bi-receipt-cutoff"></i>
                <span>Ventas</span>
            </button>
            <div class="collapse" id="menuVentas">
                <ul class="btn-toggle-nav list-unstyled fw-normal pb-1 small">
                    <li><a class="nav-link" href="index.php?controller=Venta&action=nueva">Nueva venta</a></li>
                    <li><a class="nav-link" href="index.php?controller=Venta&action=index">Listado de ventas</a></li>
                </ul>
            </div>
        </div>

        <div class="nav-item">
            <button class="btn-toggle align-items-center rounded collapsed" data-bs-toggle="collapse" data-bs-target="#menuProductos" aria-expanded="false">
                <i class="bi bi-box-seam"></i>
                <span>Productos</span>
            </button>
            <div class="collapse" id="menuProductos">
                <ul class="btn-toggle-nav list-unstyled fw-normal pb-1 small">
                    <li><a class="nav-link" href="index.php?controller=Producto&action=index">Listado</a></li>
                    <li><a class="nav-link" href="index.php?controller=Producto&action=crear">Crear producto</a></li>
                </ul>
            </div>
        </div>

        <div class="nav-item">
            <button class="btn-toggle align-items-center rounded collapsed" data-bs-toggle="collapse" data-bs-target="#menuProveedores" aria-expanded="false">
                <i class="bi bi-truck"></i>
                <span>Proveedores</span>
            </button>
            <div class="collapse" id="menuProveedores">
                <ul class="btn-toggle-nav list-unstyled fw-normal pb-1 small">
                    <li><a class="nav-link" href="index.php?controller=Proveedor&action=index">Listado</a></li>
                    <li><a class="nav-link" href="index.php?controller=Proveedor&action=crear">Crear proveedor</a></li>
                </ul>
            </div>
        </div>

        <div class="nav-item">
            <button class="btn-toggle align-items-center rounded collapsed" data-bs-toggle="collapse" data-bs-target="#menuClientes" aria-expanded="false">
                <i class="bi bi-person-badge"></i>
                <span>Clientes</span>
            </button>
            <div class="collapse" id="menuClientes">
                <ul class="btn-toggle-nav list-unstyled fw-normal pb-1 small">
                    <li><a class="nav-link" href="index.php?controller=Cliente&action=index">Listado</a></li>
                    <li><a class="nav-link" href="index.php?controller=Cliente&action=crear">Crear cliente</a></li>
                </ul>
            </div>
        </div>

        <div class="nav-item">
            <button class="btn-toggle align-items-center rounded collapsed" data-bs-toggle="collapse" data-bs-target="#menuPagos" aria-expanded="false">
                <i class="bi bi-credit-card"></i>
                <span>Métodos de pago</span>
            </button>
            <div class="collapse" id="menuPagos">
                <ul class="btn-toggle-nav list-unstyled fw-normal pb-1 small">
                    <li><a class="nav-link" href="index.php?controller=MetodoPago&action=index">Listado</a></li>
                    <li><a class="nav-link" href="index.php?controller=MetodoPago&action=crear">Crear método</a></li>
                </ul>
            </div>
        </div>

        <div class="nav-item">
            <button class="btn-toggle align-items-center rounded collapsed" data-bs-toggle="collapse" data-bs-target="#menuSucursales" aria-expanded="false">
                <i class="bi bi-building"></i>
                <span>Sucursales y depósitos</span>
            </button>
            <div class="collapse" id="menuSucursales">
                <ul class="btn-toggle-nav list-unstyled fw-normal pb-1 small">
                    <li><a class="nav-link" href="index.php?controller=Sucursal&action=index">Sucursales</a></li>
                    <li><a class="nav-link" href="index.php?controller=PuntoVenta&action=index">Puntos de venta</a></li>
                    <li><a class="nav-link" href="index.php?controller=PuntoVenta&action=crear">Crear punto de venta</a></li>
                    <li><a class="nav-link" href="index.php?controller=Deposito&action=index">Depósitos</a></li>
                </ul>
            </div>
        </div>

        <div class="nav-item">
            <button class="btn-toggle align-items-center rounded collapsed" data-bs-toggle="collapse" data-bs-target="#menuCajas" aria-expanded="false">
                <i class="bi bi-cash-coin"></i>
                <span>Cajas</span>
            </button>
            <div class="collapse" id="menuCajas">
                <ul class="btn-toggle-nav list-unstyled fw-normal pb-1 small">
                    <li><a class="nav-link" href="index.php?controller=Caja&action=index">Listado</a></li>
                    <li><a class="nav-link" href="index.php?controller=Caja&action=abrir">Abrir caja</a></li>
                </ul>
            </div>
        </div>

        <div class="nav-item">
            <button class="btn-toggle align-items-center rounded collapsed" data-bs-toggle="collapse" data-bs-target="#menuReportes" aria-expanded="false">
                <i class="bi bi-bar-chart-line-fill"></i>
                <span>Reportes</span>
            </button>
            <div class="collapse" id="menuReportes">
                <ul class="btn-toggle-nav list-unstyled fw-normal pb-1 small">
                    <li><a class="nav-link" href="index.php?controller=Reporte&action=ventas">Ventas</a></li>
                </ul>
            </div>
        </div>

        <?php if (isset($_SESSION['user']['rol_nombre']) && in_array($_SESSION['user']['rol_nombre'], ['Administrador', 'Superusuario'])): ?>
        <div class="nav-item">
            <button class="btn-toggle align-items-center rounded collapsed" data-bs-toggle="collapse" data-bs-target="#menuConfig" aria-expanded="false">
                <i class="bi bi-gear-fill"></i>
                <span>Configuración</span>
            </button>
            <div class="collapse" id="menuConfig">
                <ul class="btn-toggle-nav list-unstyled fw-normal pb-1 small">
                    <?php if ($_SESSION['user']['rol_nombre'] === 'Superusuario'): ?>
                    <li><a class="nav-link" href="index.php?controller=Configuracion&action=empresas">Empresas</a></li>
                    <?php endif; ?>
                    <li><a class="nav-link" href="index.php?controller=Configuracion&action=sucursales">Sucursales</a></li>
                    <li><a class="nav-link" href="index.php?controller=Usuario&action=index">Usuarios</a></li>
                    <li><a class="nav-link" href="index.php?controller=Configuracion&action=index">Datos de la empresa</a></li>
                    <li><a class="nav-link" href="index.php?controller=Configuracion&action=manejoBd">Manejo de base de datos</a></li>
                </ul>
            </div>
        </div>
        <?php endif; ?>

        <a class="nav-link" href="index.php?controller=Backup&action=index">
            <i class="bi bi-hdd-stack"></i>
            <span>Backup y Restauración</span>
        </a>

        <a class="nav-link" href="index.php?controller=Log&action=index">
            <i class="bi bi-clipboard-data"></i>
            <span>Logs</span>
        </a>
    </nav>

</div>
