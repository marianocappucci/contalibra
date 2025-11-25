<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h3>Sucursales</h3>
        <a href="index.php?controller=Sucursal&action=crear" class="btn btn-primary">Nueva sucursal</a>
    </div>
    <table class="table table-striped">
        <thead>
            <tr>
                <th>Nombre</th>
                <th>Empresa</th>
                <th>Dirección</th>
                <th>Ciudad</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($sucursales as $s): ?>
            <tr>
                <td><?php echo htmlspecialchars($s['nombre']); ?></td>
                <td><?php echo htmlspecialchars($s['empresa_nombre'] ?? ''); ?></td>
                <td><?php echo htmlspecialchars($s['direccion']); ?></td>
                <td><?php echo htmlspecialchars($s['ciudad']); ?></td>
                <td>
                    <a href="index.php?controller=Sucursal&action=editar&id=<?php echo $s['id']; ?>" class="btn btn-sm btn-warning">Editar</a>
                    <a href="index.php?controller=Sucursal&action=eliminar&id=<?php echo $s['id']; ?>" class="btn btn-sm btn-danger" onclick="return confirm('¿Eliminar sucursal?');">Eliminar</a>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
