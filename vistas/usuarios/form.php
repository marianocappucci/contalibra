<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">

<div class="container">
  <h3><?php echo $usuario ? 'Editar usuario' : 'Nuevo usuario'; ?></h3>
  <form method="post">
    <div class="row">
      <div class="col-md-6 mb-3">
        <label class="form-label">Nombre</label>
        <input type="text" name="nombre" class="form-control" required value="<?php echo $usuario['nombre'] ?? ''; ?>">
      </div>
      <div class="col-md-3 mb-3">
        <label class="form-label">Usuario</label>
        <input type="text" name="username" class="form-control" required value="<?php echo $usuario['username'] ?? ''; ?>">
      </div>
      <?php if(!$usuario): ?>
      <div class="col-md-3 mb-3">
        <label class="form-label">Contraseña</label>
        <input type="text" name="password" class="form-control" required value="1234">
      </div>
      <?php endif; ?>
      <div class="col-md-3 mb-3">
        <label class="form-label">Rol</label>
        <select name="rol_id" class="form-select" required>
          <?php foreach ($roles as $r): ?>
            <option value="<?php echo $r['id']; ?>" <?php echo ($usuario && $usuario['rol_id']==$r['id'])?'selected':''; ?>>
              <?php echo htmlspecialchars($r['nombre']); ?>
            </option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="col-md-3 mb-3 form-check">
        <input class="form-check-input" type="checkbox" name="activo" id="activo" <?php echo (!$usuario || $usuario['activo'])?'checked':''; ?>>
        <label class="form-check-label" for="activo">Activo</label>
      </div>
    </div>
    <button class="btn btn-success">Guardar</button>
    <a href="index.php?controller=Usuario&action=index" class="btn btn-secondary">Volver</a>
  </form>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
