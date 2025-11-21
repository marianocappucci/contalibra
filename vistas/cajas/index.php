<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">

<div class="container">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h3>Cajas</h3>
    <a href="index.php?controller=Caja&action=abrir" class="btn btn-primary">Abrir caja</a>
  </div>
  <table class="table table-striped">
    <thead>
      <tr>
        <th>ID</th>
        <th>Nombre</th>
        <th>Estado</th>
        <th>Saldo inicial</th>
        <th>Saldo final</th>
        <th>Usuario apertura</th>
        <th>Fecha apertura</th>
        <th>Fecha cierre</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <?php foreach ($cajas as $c): ?>
      <tr>
        <td><?php echo $c['id']; ?></td>
        <td><?php echo htmlspecialchars($c['nombre']); ?></td>
        <td><?php echo $c['estado']; ?></td>
        <td>$<?php echo number_format($c['saldo_inicial'], 2); ?></td>
        <td>$<?php echo number_format($c['saldo_final'], 2); ?></td>
        <td><?php echo htmlspecialchars($c['usuario_apertura']); ?></td>
        <td><?php echo $c['fecha_apertura']; ?></td>
        <td><?php echo $c['fecha_cierre']; ?></td>
        <td>
          <?php if($c['estado']=='ABIERTA'): ?>
          <a href="index.php?controller=Caja&action=cerrar&id=<?php echo $c['id']; ?>" class="btn btn-sm btn-warning">Cerrar</a>
          <?php endif; ?>
        </td>
      </tr>
      <?php endforeach; ?>
    </tbody>
  </table>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
