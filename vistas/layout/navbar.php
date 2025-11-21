<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container-fluid">
    <a class="navbar-brand" href="index.php?controller=Dashboard&action=index">POS MVC</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav me-auto mb-2 mb-lg-0">
        <li class="nav-item"><a class="nav-link" href="index.php?controller=Venta&action=nueva">Nueva venta</a></li>
        <li class="nav-item"><a class="nav-link" href="index.php?controller=Venta&action=index">Ventas</a></li>
        <li class="nav-item"><a class="nav-link" href="index.php?controller=Producto&action=index">Productos</a></li>
        <li class="nav-item"><a class="nav-link" href="index.php?controller=Caja&action=index">Cajas</a></li>
        <li class="nav-item"><a class="nav-link" href="index.php?controller=Usuario&action=index">Usuarios</a></li>
        <li class="nav-item"><a class="nav-link" href="index.php?controller=Reporte&action=ventas">Reportes</a></li>
        <?php if (isset($_SESSION['user']) && $_SESSION['user']['rol_nombre'] === 'Administrador'): ?>
        <li class="nav-item"><a class="nav-link" href="index.php?controller=Configuracion&action=index">Configuración</a></li>
        <?php endif; ?>
      </ul>
      <span class="navbar-text me-3">
        <?php if(isset($_SESSION['user'])): ?>
            <?php echo htmlspecialchars($_SESSION['user']['nombre']); ?> (<?php echo htmlspecialchars($_SESSION['user']['rol_nombre']); ?>)
        <?php endif; ?>
      </span>
      <a href="index.php?controller=Auth&action=logout" class="btn btn-outline-light">Salir</a>
    </div>
  </div>
</nav>
