<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">


<?php 
$configModel = new Configuracion();
$conf = $configModel->get();
?>

<div class="container">
  <div class="mb-3">
    <h4><?php echo htmlspecialchars($conf['nombre_fantasia']); ?></h4>
    <p>
      <?php echo htmlspecialchars($conf['direccion']); ?><br>
      Tel: <?php echo htmlspecialchars($conf['telefono']); ?><br>
      CUIT: <?php echo htmlspecialchars($conf['cuit']); ?><br>
      Punto de venta: <?php echo htmlspecialchars($conf['punto_venta']); ?>
    </p>
  </div>

  <h3>Comprobante de venta #<?php echo $venta['id']; ?></h3>
  <p><strong>Fecha:</strong> <?php echo $venta['fecha']; ?></p>
  <p><strong>Cliente:</strong> <?php echo htmlspecialchars($venta['cliente_nombre'] ?: $venta['cliente']); ?></p>
  <p><strong>Método de pago:</strong> <?php echo htmlspecialchars($venta['metodo_pago_nombre']); ?> | <strong>Sucursal:</strong> <?php echo htmlspecialchars($venta['sucursal_nombre']); ?></p>
  <p><strong>Estado:</strong> <?php echo $venta['estado']; ?></p>
  <p><strong>CAE:</strong> <?php echo $venta['cae']; ?> (vto: <?php echo $venta['cae_vencimiento']; ?>)</p>

  <table class="table table-bordered">
    <thead>
      <tr>
        <th>Producto</th>
        <th>Cantidad</th>
        <th>Precio unitario</th>
        <th>Total</th>
      </tr>
    </thead>
    <tbody>
      <?php foreach ($venta['items'] as $it): ?>
      <tr>
        <td><?php echo htmlspecialchars($it['producto_nombre']); ?></td>
        <td><?php echo $it['cantidad']; ?></td>
        <td>$<?php echo number_format($it['precio_unitario'], 2); ?></td>
        <td>$<?php echo number_format($it['total'], 2); ?></td>
      </tr>
      <?php endforeach; ?>
    </tbody>
  </table>

  <div class="row justify-content-end">
    <div class="col-md-4">
      <ul class="list-group">
        <li class="list-group-item d-flex justify-content-between">
          <span>Subtotal</span>
          <strong>$<?php echo number_format($venta['subtotal'], 2); ?></strong>
        </li>
        <li class="list-group-item d-flex justify-content-between">
          <span>IVA 21%</span>
          <strong>$<?php echo number_format($venta['iva'], 2); ?></strong>
        </li>
        <li class="list-group-item d-flex justify-content-between">
          <span>Total</span>
          <strong>$<?php echo number_format($venta['total'], 2); ?></strong>
        </li>
      </ul>
    </div>
  </div>

  <a href="index.php?controller=Venta&action=index" class="btn btn-secondary mt-3">Volver</a>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
