<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">


<div class="container">
  <h3>Configuración del Negocio</h3>

  <?php if (!empty($mensaje)): ?>
    <div class="alert alert-success"><?php echo $mensaje; ?></div>
  <?php endif; ?>

  <form method="post" class="mt-3">
    <div class="row">
      <div class="col-md-6 mb-3">
        <label class="form-label">Nombre de fantasía</label>
        <input type="text" name="nombre_fantasia" class="form-control"
               value="<?php echo htmlspecialchars($config['nombre_fantasia']); ?>" required>
      </div>

      <div class="col-md-6 mb-3">
        <label class="form-label">Dirección</label>
        <input type="text" name="direccion" class="form-control"
               value="<?php echo htmlspecialchars($config['direccion']); ?>">
      </div>

      <div class="col-md-4 mb-3">
        <label class="form-label">Teléfono</label>
        <input type="text" name="telefono" class="form-control"
               value="<?php echo htmlspecialchars($config['telefono']); ?>">
      </div>

      <div class="col-md-4 mb-3">
        <label class="form-label">CUIT</label>
        <input type="text" name="cuit" class="form-control"
               value="<?php echo htmlspecialchars($config['cuit']); ?>">
      </div>

      <div class="col-md-4 mb-3">
        <label class="form-label">Punto de venta</label>
        <input type="text" name="punto_venta" class="form-control"
               value="<?php echo htmlspecialchars($config['punto_venta']); ?>">
      </div>
    </div>

    <button class="btn btn-success">Guardar cambios</button>
    <a href="index.php?controller=Dashboard&action=index" class="btn btn-secondary">Volver</a>
  </form>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
