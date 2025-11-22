<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">

<style>
    #sidebar {
        width: 250px;
        height: calc(100vh - 60px);
        background: #1f1f1f;
        color: white;
        position: fixed;
        left: 0;
        top: 60px;
        overflow-y: auto;
        padding-top: 12px; /* deja espacio mínimo tras el logo del topbar */
    }

    /* Contalibra dentro del sidebar */
    #sidebar .sidebar-title {
        font-size: 1.3rem;
        font-weight: 700;
        padding: 18px 20px;
        border-bottom: 1px solid #343434;
        display: flex;
        align-items: center;
        gap: 10px;
        background: #252525;
        position: sticky;
        top: 60px; /* justo debajo de la topbar */
        z-index: 10;
    }

    #sidebar .sidebar-title i {
        font-size: 1.5rem;
    }

    #sidebar .nav-link {
        color: #ddd;
        padding: 10px 20px;
        font-size: 0.95rem;
    }

    #sidebar .nav-link:hover {
        background: #343434;
        color: #fff;
    }

    #sidebar .bi {
        margin-right: 8px;
    }

    #content {
        margin-left: 250px;
        padding: 20px;
        padding-top: 80px;
        transition: margin-left 0.3s ease;
    }
</style>

<div id="sidebar">

    <!-- TÍTULO DENTRO DEL SIDEBAR (este es el que querías) -->
  

    <ul class="nav flex-column mt-2">

        <li class="nav-item">
            <a class="nav-link" href="index.php?controller=Dashboard&action=index">
                <i class="bi bi-house-door-fill"></i> Principal
            </a>
        </li>

        <!-- Ventas -->
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="collapse" href="#menuVentas">
                <i class="bi bi-receipt-cutoff"></i> Ventas
            </a>
            <div class="collapse" id="menuVentas">
                <a class="nav-link ms-4" href="index.php?controller=Venta&action=nueva">Nueva venta</a>
                <a class="nav-link ms-4" href="index.php?controller=Venta&action=index">Listado de ventas</a>
            </div>
        </li>

        <!-- Productos -->
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="collapse" href="#menuProductos">
                <i class="bi bi-box-seam"></i> Productos
            </a>
            <div class="collapse" id="menuProductos">
                <a class="nav-link ms-4" href="index.php?controller=Producto&action=index">Listado</a>
                <a class="nav-link ms-4" href="index.php?controller=Producto&action=crear">Crear producto</a>
            </div>
        </li>

        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="collapse" href="#menuProveedores">
                <i class="bi bi-truck"></i> Proveedores
            </a>
            <div class="collapse" id="menuProveedores">
                <a class="nav-link ms-4" href="index.php?controller=Proveedor&action=index">Listado</a>
                <a class="nav-link ms-4" href="index.php?controller=Proveedor&action=crear">Crear proveedor</a>
            </div>
        </li>

        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="collapse" href="#menuClientes">
                <i class="bi bi-person-badge"></i> Clientes
            </a>
            <div class="collapse" id="menuClientes">
                <a class="nav-link ms-4" href="index.php?controller=Cliente&action=index">Listado</a>
                <a class="nav-link ms-4" href="index.php?controller=Cliente&action=crear">Crear cliente</a>
            </div>
        </li>

        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="collapse" href="#menuPagos">
                <i class="bi bi-credit-card"></i> Métodos de pago
            </a>
            <div class="collapse" id="menuPagos">
                <a class="nav-link ms-4" href="index.php?controller=MetodoPago&action=index">Listado</a>
                <a class="nav-link ms-4" href="index.php?controller=MetodoPago&action=crear">Crear método</a>
            </div>
        </li>

        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="collapse" href="#menuSucursales">
                <i class="bi bi-building"></i> Sucursales y depósitos
            </a>
            <div class="collapse" id="menuSucursales">
                <a class="nav-link ms-4" href="index.php?controller=Sucursal&action=index">Sucursales</a>
                <a class="nav-link ms-4" href="index.php?controller=Deposito&action=index">Depósitos</a>
            </div>
        </li>

        <!-- Cajas -->
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="collapse" href="#menuCajas">
                <i class="bi bi-cash-coin"></i> Cajas
            </a>
            <div class="collapse" id="menuCajas">
                <a class="nav-link ms-4" href="index.php?controller=Caja&action=index">Listado</a>
                <a class="nav-link ms-4" href="index.php?controller=Caja&action=abrir">Abrir caja</a>
            </div>
        </li>

        <!-- Usuarios -->
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="collapse" href="#menuUsuarios">
                <i class="bi bi-people-fill"></i> Usuarios
            </a>
            <div class="collapse" id="menuUsuarios">
                <a class="nav-link ms-4" href="index.php?controller=Usuario&action=index">Listado</a>
                <a class="nav-link ms-4" href="index.php?controller=Usuario&action=crear">Crear usuario</a>
            </div>
        </li>

        <!-- Reportes -->
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="collapse" href="#menuReportes">
                <i class="bi bi-bar-chart-line-fill"></i> Reportes
            </a>
            <div class="collapse" id="menuReportes">
                <a class="nav-link ms-4" href="index.php?controller=Reporte&action=ventas">Ventas</a>
            </div>
        </li>

        <!-- Configuración (solo admin) -->
        <?php if ($_SESSION['user']['rol_nombre'] === 'Administrador'): ?>
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="collapse" href="#menuConfig">
                <i class="bi bi-gear-fill"></i> Configuración
            </a>
            <div class="collapse" id="menuConfig">
                <a class="nav-link ms-4" href="index.php?controller=Configuracion&action=index">Datos del negocio</a>
            </div>
        </li>
        <?php endif; ?>
        <?php if ($_SESSION['user']['rol_nombre'] === 'Superusuario'): ?>
        <li class="nav-item">
            <a class="nav-link" href="index.php?controller=Superusuario&action=crearBase">
                <i class="bi bi-shield-lock"></i> Bases para empresas
            </a>
        </li>
        <?php endif; ?>
<li class="nav-item">
    <a class="nav-link" href="index.php?controller=Backup&action=index">
        <i class="bi bi-hdd-stack"></i> Backup y Restauración
    </a>
</li>

    <li class='nav-item'><a class='nav-link' href='index.php?controller=Log&action=index'><i class='bi bi-clipboard-data'></i> Logs</a></li></ul>
</div>
