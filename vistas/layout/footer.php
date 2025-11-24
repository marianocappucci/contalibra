<?php
    $sucursalActivaNombre = 'Sucursal no definida';

    try {
        $sucursalModel = new Sucursal();
        $sucursalId = $_SESSION['sucursal_id'] ?? null;

        if ($sucursalId) {
            $sucursal = $sucursalModel->getById($sucursalId);
            $sucursalActivaNombre = $sucursal['nombre'] ?? $sucursalActivaNombre;
        }

        if ($sucursalActivaNombre === 'Sucursal no definida') {
            $sucursales = $sucursalModel->getAll();
            if (!empty($sucursales)) {
                $sucursalActivaNombre = $sucursales[0]['nombre'];
            }
        }
    } catch (Exception $e) {
        // Si no se puede obtener, dejamos el mensaje por defecto.
    }
?>

<footer class="status-footer">
  <div class="container d-flex justify-content-end align-items-center">
      <span class="status-message ms-auto"><?php echo htmlspecialchars($sucursalActivaNombre); ?></span>
  </div>
</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="public/js/app.js"></script>
</body>
</html>
