<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">

<div class="container">
  <h3><?php echo $producto ? 'Editar producto' : 'Nuevo producto'; ?></h3>
  <form method="post">
    <div class="row">
      <div class="col-md-6 mb-3">
        <label class="form-label">Nombre</label>
        <input type="text" name="nombre" class="form-control" required value="<?php echo $producto['nombre'] ?? ''; ?>">
      </div>
      <div class="col-md-3 mb-3">
        <label class="form-label">SKU</label>
        <input type="text" name="sku" class="form-control" required value="<?php echo $producto['sku'] ?? ''; ?>">
      </div>
      <div class="col-md-3 mb-3">
        <label class="form-label">Código de barras</label>
        <input type="text" name="codigo_barras" class="form-control" value="<?php echo $producto['codigo_barras'] ?? ''; ?>">
      </div>
      <div class="col-md-3 mb-3">
        <label class="form-label">Lista de precios</label>
        <select name="lista_precio_id" class="form-select" required>
          <?php foreach ($listas as $l): ?>
            <option value="<?php echo $l['id']; ?>" <?php echo ($producto && $producto['lista_precio_id']==$l['id'])?'selected':''; ?>>
              <?php echo htmlspecialchars($l['nombre']); ?>
            </option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="col-md-3 mb-3">
        <label class="form-label">Precio</label>
        <input type="number" step="0.01" name="precio" class="form-control" required value="<?php echo $producto['precio'] ?? '0'; ?>">
      </div>
      <div class="col-md-4 mb-3">
        <label class="form-label">Proveedor</label>
        <select name="proveedor_id" class="form-select">
          <option value="">Sin asignar</option>
          <?php foreach ($proveedores as $prov): ?>
            <option value="<?php echo $prov['id']; ?>" <?php echo (($producto['proveedor_id'] ?? '')==$prov['id'])?'selected':''; ?>><?php echo htmlspecialchars($prov['nombre']); ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="col-md-4 mb-3">
        <label class="form-label">Depósito</label>
        <select name="deposito_id" class="form-select">
          <option value="">Sin asignar</option>
          <?php foreach ($depositos as $dep): ?>
            <option value="<?php echo $dep['id']; ?>" <?php echo (($producto['deposito_id'] ?? '')==$dep['id'])?'selected':''; ?>><?php echo htmlspecialchars($dep['nombre']); ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="col-md-3 mb-3">
        <label class="form-label">Stock inicial</label>
        <input type="number" step="0.01" name="stock" class="form-control" required value="<?php echo $producto['stock'] ?? '0'; ?>">
      </div>
      <div class="col-md-3 mb-3 form-check">
        <input class="form-check-input" type="checkbox" name="activo" id="activo" <?php echo (!$producto || $producto['activo'])?'checked':''; ?>>
        <label class="form-check-label" for="activo">Activo</label>
      </div>
    </div>
    <button class="btn btn-success">Guardar</button>
    <a href="index.php?controller=Producto&action=index" class="btn btn-secondary">Volver</a>
  </form>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
