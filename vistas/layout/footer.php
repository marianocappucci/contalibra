<?php
  $baseActiva = $_SESSION['db_name'] ?? ($_SESSION['user']['base_datos'] ?? null);
  $empresaActiva = $baseActiva;

  try {
    if (class_exists('Configuracion')) {
      $configuracionModel = new Configuracion();
      $configuracion = $configuracionModel->get();
      if (!empty($configuracion['nombre_fantasia'])) {
        $empresaActiva = $configuracion['nombre_fantasia'];
      }
    }
  } catch (Exception $e) {
    // Si la consulta falla, se mantiene el valor por defecto
  }

  $empresaActiva = $empresaActiva ?: 'No configurada';
?>

<footer class="app-footer">
  <div class="d-flex justify-content-end align-items-center">
    <span class="small">Empresa activa: <?php echo htmlspecialchars($empresaActiva); ?></span>
  </div>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="public/js/app.js"></script>
  </body>
</html>
