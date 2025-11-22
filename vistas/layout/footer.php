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

<footer class="status-footer">
  <div class="container d-flex justify-content-between align-items-center">
    <span class="status-label">Estado</span>
    <div class="d-flex align-items-center">
      <span class="status-indicator" aria-hidden="true"></span>
      <span class="status-message"><?php echo htmlspecialchars($empresaActivaNombre); ?></span>
    </div>
  </div>
</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="public/js/app.js"></script>
</body>
</html>
