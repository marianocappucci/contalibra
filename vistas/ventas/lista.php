<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">

<div class="container">
  <h3>Ventas</h3>
  <table class="table table-striped">
    <thead>
      <tr>
        <th>ID</th>
        <th>Fecha</th>
        <th>Cliente</th>
        <th>Total</th>
        <th>Estado</th>
        <th>CAE</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <?php foreach ($ventas as $v): ?>
      <tr>
        <td><?php echo $v['id']; ?></td>
        <td><?php echo $v['fecha']; ?></td>
        <td><?php echo htmlspecialchars($v['cliente']); ?></td>
        <td>$<?php echo number_format($v['total'], 2); ?></td>
        <td><?php echo $v['estado']; ?></td>
        <td><?php echo $v['cae']; ?></td>
        <td><a href="index.php?controller=Venta&action=ver&id=<?php echo $v['id']; ?>" class="btn btn-sm btn-primary">Ver</a></td>
      </tr>
      <?php endforeach; ?>
    </tbody>
  </table>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
