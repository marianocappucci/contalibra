<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">

<div class="container">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h3>Usuarios</h3>
    <a href="index.php?controller=Usuario&action=crear" class="btn btn-primary">Nuevo usuario</a>
  </div>
  <table class="table table-striped">
    <thead>
      <tr>
        <th>ID</th>
        <th>Nombre</th>
        <th>Usuario</th>
        <th>Rol</th>
        <th>Activo</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <?php foreach ($usuarios as $u): ?>
      <tr>
        <td><?php echo $u['id']; ?></td>
        <td><?php echo htmlspecialchars($u['nombre']); ?></td>
        <td><?php echo htmlspecialchars($u['username']); ?></td>
        <td><?php echo htmlspecialchars($u['rol_nombre']); ?></td>
        <td><?php echo $u['activo'] ? 'Sí' : 'No'; ?></td>
        <td>
          <a href="index.php?controller=Usuario&action=editar&id=<?php echo $u['id']; ?>" class="btn btn-sm btn-warning">Editar</a>
          <a href="index.php?controller=Usuario&action=eliminar&id=<?php echo $u['id']; ?>" class="btn btn-sm btn-danger" onclick="return confirm('¿Eliminar usuario?');">Eliminar</a>
        </td>
      </tr>
      <?php endforeach; ?>
    </tbody>
  </table>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>
