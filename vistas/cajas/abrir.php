<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">

<div class="container">
  <h3>Abrir caja</h3>
  <?php if (!empty($error)): ?>
    <div class="alert alert-danger" role="alert">
      <?php echo $error; ?>
    </div>
  <?php endif; ?>
  <form method="post">
    <div class="mb-3">
      <label class="form-label">Nombre de caja</label>
      <input type="text" name="nombre" class="form-control" required value="Caja principal">
    </div>
    <div class="mb-3">
      <label class="form-label">Saldo inicial</label>
      <input type="number" step="0.01" name="saldo_inicial" class="form-control" required value="0">
    </div>
    <button class="btn btn-success">Abrir</button>
    <a href="index.php?controller=Caja&action=index" class="btn btn-secondary">Volver</a>
  </form>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
