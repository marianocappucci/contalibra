<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">

<div class="container">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h3>Productos</h3>
    <a href="index.php?controller=Producto&action=crear" class="btn btn-primary">Nuevo producto</a>
  </div>
  <table class="table table-striped">
    <thead>
      <tr>
        <th>ID</th>
        <th>Nombre</th>
        <th>SKU</th>
        <th>Lista</th>
        <th>Precio</th>
        <th>Stock</th>
        <th>Activo</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <?php foreach ($productos as $p): ?>
      <tr>
        <td><?php echo $p['id']; ?></td>
        <td><?php echo htmlspecialchars($p['nombre']); ?></td>
        <td><?php echo htmlspecialchars($p['sku']); ?></td>
        <td><?php echo htmlspecialchars($p['lista_nombre']); ?></td>
        <td>$<?php echo number_format($p['precio'], 2); ?></td>
        <td><?php echo $p['stock']; ?></td>
        <td><?php echo $p['activo'] ? 'Sí' : 'No'; ?></td>
        <td>
          <a href="index.php?controller=Producto&action=editar&id=<?php echo $p['id']; ?>" class="btn btn-sm btn-warning">Editar</a>
          <a href="index.php?controller=Producto&action=eliminar&id=<?php echo $p['id']; ?>" class="btn btn-sm btn-danger" onclick="return confirm('¿Eliminar producto?');">Eliminar</a>
        </td>
      </tr>
      <?php endforeach; ?>
    </tbody>
  </table>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
