<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
  <div class="container">
    <h3>Manejo de base de datos</h3>
    <p class="text-muted">Crea una nueva base de datos para una empresa y asígnala rápidamente a un usuario.</p>

    <?php if (!empty($mensaje)): ?>
      <div class="alert alert-success"><?php echo htmlspecialchars($mensaje); ?></div>
    <?php endif; ?>

    <?php if (!empty($error)): ?>
      <div class="alert alert-danger"><?php echo htmlspecialchars($error); ?></div>
    <?php endif; ?>

    <form method="post" class="mt-3">
      <div class="row">
        <div class="col-md-6 mb-3">
          <label class="form-label">Nombre de la empresa</label>
          <input type="text" name="empresa_nombre" class="form-control" required placeholder="Comercio Ejemplo S.R.L."
                 value="<?php echo htmlspecialchars($_POST['empresa_nombre'] ?? ''); ?>">
        </div>

        <div class="col-md-6 mb-3">
          <label class="form-label">Nombre de la base de datos</label>
          <input type="text" name="nombre_bd" class="form-control" required placeholder="contadb_empresa"
                 value="<?php echo htmlspecialchars($_POST['nombre_bd'] ?? ''); ?>">
          <div class="form-text">Usa solo letras, números y guiones bajos.</div>
        </div>
      </div>

      <div class="row">
        <div class="col-md-6 mb-3">
          <label class="form-label">Asignar a usuario (opcional)</label>
          <select name="usuario_id" class="form-select">
            <option value="">No asignar por ahora</option>
            <?php foreach ($usuarios as $u): ?>
              <option value="<?php echo $u['id']; ?>" <?php echo (($_POST['usuario_id'] ?? '') == $u['id']) ? 'selected' : ''; ?>>
                <?php echo htmlspecialchars($u['nombre'] . ' (' . ($u['rol_nombre'] ?? '') . ')'); ?>
              </option>
            <?php endforeach; ?>
          </select>
          <div class="form-text">Al asignar, el usuario trabajará sobre la nueva base de datos.</div>
        </div>
      </div>

      <button class="btn btn-success">Crear base</button>
      <a href="index.php?controller=Dashboard&action=index" class="btn btn-secondary">Cancelar</a>
    </form>
  </div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
