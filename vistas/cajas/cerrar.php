<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">

<div class="container">
  <h3>Cerrar caja</h3>
  <form method="post">
    <div class="mb-3">
      <label class="form-label">Saldo final</label>
      <input type="number" step="0.01" name="saldo_final" class="form-control" required>
    </div>
    <button class="btn btn-success">Cerrar caja</button>
    <a href="index.php?controller=Caja&action=index" class="btn btn-secondary">Volver</a>
  </form>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
