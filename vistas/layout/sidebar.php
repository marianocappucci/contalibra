<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">

<style>
    #sidebar {
        width: 250px;
        min-height: 100vh;
        background: #1f1f1f;
        color: white;
        position: fixed;
        left: 0;
        top: 60px;
        padding-top: 60px; /* deja espacio para la topbar */
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
<li class="nav-item">
    <a class="nav-link" href="index.php?controller=Backup&action=index">
        <i class="bi bi-hdd-stack"></i> Backup y Restauración
    </a>
</li>

    </ul>
</div>
