<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">

<div class="container">
  <h3>Reporte de ventas</h3>
  <form class="row g-3 mb-3" method="get">
    <input type="hidden" name="controller" value="Reporte">
    <input type="hidden" name="action" value="ventas">
    <div class="col-md-3">
      <label class="form-label">Desde</label>
      <input type="date" name="desde" class="form-control" value="<?php echo htmlspecialchars($desde ?? ''); ?>">
    </div>
    <div class="col-md-3">
      <label class="form-label">Hasta</label>
      <input type="date" name="hasta" class="form-control" value="<?php echo htmlspecialchars($hasta ?? ''); ?>">
    </div>
    <div class="col-md-3 align-self-end">
      <button class="btn btn-primary">Filtrar</button>
    </div>
  </form>

  <table class="table table-striped">
    <thead>
      <tr>
        <th>ID</th>
        <th>Fecha</th>
        <th>Cliente</th>
        <th>Total</th>
        <th>Estado</th>
      </tr>
    </thead>
    <tbody>
      <?php 
      $totalGeneral = 0;
      foreach ($ventas as $v): 
        $totalGeneral += $v['total'];
      ?>
      <tr>
        <td><?php echo $v['id']; ?></td>
        <td><?php echo $v['fecha']; ?></td>
        <td><?php echo htmlspecialchars($v['cliente']); ?></td>
        <td>$<?php echo number_format($v['total'], 2); ?></td>
        <td><?php echo $v['estado']; ?></td>
      </tr>
      <?php endforeach; ?>
    </tbody>
    <tfoot>
      <tr>
        <th colspan="3" class="text-end">Total general:</th>
        <th>$<?php echo number_format($totalGeneral, 2); ?></th>
        <th></th>
      </tr>
    </tfoot>
  </table>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
