<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
  <div class="container">
    <h3>Empresas</h3>
    <p class="text-muted">Crea una nueva empresa, asigna un ID y genera automáticamente su base de datos <code>contadb_{nombre}</code>.</p>

    <?php if (!empty($mensaje)): ?>
      <div class="alert alert-success"><?php echo htmlspecialchars($mensaje); ?></div>
    <?php endif; ?>

    <?php if (!empty($error)): ?>
      <div class="alert alert-danger"><?php echo htmlspecialchars($error); ?></div>
    <?php endif; ?>

    <form method="post" class="mt-3">
      <div class="row g-3 align-items-end">
        <div class="col-md-6">
          <label class="form-label">Nombre de la empresa</label>
          <input type="text" name="empresa_nombre" class="form-control" required
                 value="<?php echo htmlspecialchars($_POST['empresa_nombre'] ?? ''); ?>"
                 placeholder="Comercio Ejemplo">
        </div>
        <div class="col-md-6">
          <label class="form-label">Base de datos generada</label>
          <input type="text" class="form-control" value="<?php echo htmlspecialchars($dbPreview ?: 'contadb_nombre_empresa'); ?>" readonly>
          <div class="form-text">Se genera a partir del nombre ingresado con el prefijo <code>contadb_</code>.</div>
        </div>
      </div>

      <div class="mt-3">
        <button class="btn btn-success">Crear empresa</button>
        <a href="index.php?controller=Dashboard&action=index" class="btn btn-secondary">Cancelar</a>
      </div>
    </form>

    <hr class="my-4">

    <h5>Empresas registradas</h5>
    <?php if (!empty($empresas)): ?>
      <div class="table-responsive">
        <table class="table table-striped align-middle">
          <thead>
            <tr>
              <th>ID</th>
              <th>Nombre</th>
              <th>Base de datos</th>
              <th>Creada</th>
            </tr>
          </thead>
          <tbody>
          <?php foreach ($empresas as $empresa): ?>
            <tr>
              <td><?php echo htmlspecialchars($empresa['id'] ?? ''); ?></td>
              <td><?php echo htmlspecialchars($empresa['nombre'] ?? ''); ?></td>
              <td><code><?php echo htmlspecialchars($empresa['base_datos'] ?? ''); ?></code></td>
              <td><?php echo htmlspecialchars($empresa['creado_en'] ?? ''); ?></td>
            </tr>
          <?php endforeach; ?>
          </tbody>
        </table>
      </div>
    <?php else: ?>
      <p class="text-muted">Aún no hay empresas registradas.</p>
    <?php endif; ?>
  </div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
