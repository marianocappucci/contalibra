<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">


<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">

<style>
  .menu-card {
    transition: 0.2s;
    cursor: pointer;
    border-radius: 12px;
  }
  .menu-card:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 12px rgba(0,0,0,.15);
  }
  .menu-icon {
    font-size: 50px;
    margin-bottom: 10px;
    color: #0d6efd;
  }
</style>

<div class="container">
  <h3 class="mb-4">Panel Principal</h3>

  <?php if (!empty($dbFallbackMessage)): ?>
    <div class="alert alert-warning d-flex align-items-center" role="alert">
      <i class="bi bi-exclamation-triangle-fill me-3 fs-4 text-warning"></i>
      <div>
        <?php echo htmlspecialchars($dbFallbackMessage, ENT_QUOTES, 'UTF-8'); ?>
      </div>
    </div>
  <?php endif; ?>

  <?php
    $usuarioActivo = $_SESSION['user']['nombre'] ?? 'Usuario no identificado';
    $empresaActivaNombre = $empresaActiva ?? $baseActiva ?? 'No configurada';
  ?>

  <div class="alert alert-primary d-flex align-items-center" role="alert">
    <i class="bi bi-building me-3 fs-3 text-primary"></i>
    <div>
      <div class="fw-semibold">Usuario activo: <?php echo htmlspecialchars($usuarioActivo); ?></div>
      <div class="small text-muted">Empresa activa: <?php echo htmlspecialchars($empresaActivaNombre); ?></div>
      <?php if (!empty($baseActiva) && $empresaActivaNombre !== $baseActiva): ?>
        <div class="small text-muted">Base de datos: <?php echo htmlspecialchars($baseActiva); ?></div>
      <?php endif; ?>
      
    </div>
  </div>

  <div class="row g-4">

    <div class="col-md-3">
      <a href="index.php?controller=Venta&action=nueva" class="text-decoration-none text-dark">
        <div class="card text-center p-3 menu-card">
          <i class="bi bi-cart-plus-fill menu-icon"></i>
          <h5>Nueva Venta</h5>
        </div>
      </a>
    </div>

    <div class="col-md-3">
      <a href="index.php?controller=Venta&action=index" class="text-decoration-none text-dark">
        <div class="card text-center p-3 menu-card">
          <i class="bi bi-receipt-cutoff menu-icon"></i>
          <h5>Listado de Ventas</h5>
        </div>
      </a>
    </div>

    <div class="col-md-3">
      <a href="index.php?controller=Producto&action=index" class="text-decoration-none text-dark">
        <div class="card text-center p-3 menu-card">
          <i class="bi bi-box-seam-fill menu-icon"></i>
          <h5>Productos</h5>
        </div>
      </a>
    </div>

    <div class="col-md-3">
      <a href="index.php?controller=Caja&action=index" class="text-decoration-none text-dark">
        <div class="card text-center p-3 menu-card">
          <i class="bi bi-cash-coin menu-icon"></i>
          <h5>Cajas</h5>
        </div>
      </a>
    </div>

    <div class="col-md-3">
      <a href="index.php?controller=Usuario&action=index" class="text-decoration-none text-dark">
        <div class="card text-center p-3 menu-card">
          <i class="bi bi-people-fill menu-icon"></i>
          <h5>Usuarios</h5>
        </div>
      </a>
    </div>

    <div class="col-md-3">
      <a href="index.php?controller=Reporte&action=ventas" class="text-decoration-none text-dark">
        <div class="card text-center p-3 menu-card">
          <i class="bi bi-bar-chart-line-fill menu-icon"></i>
          <h5>Reportes</h5>
        </div>
      </a>
    </div>

    <?php if (isset($_SESSION['user']) && $_SESSION['user']['rol_nombre'] === 'Administrador'): ?>
    <div class="col-md-3">
      <a href="index.php?controller=Configuracion&action=index" class="text-decoration-none text-dark">
        <div class="card text-center p-3 menu-card">
          <i class="bi bi-gear-fill menu-icon"></i>
          <h5>Configuración</h5>
        </div>
      </a>
    </div>
    <?php endif; ?>

  </div>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
