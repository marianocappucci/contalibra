<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h3>Puntos de venta</h3>
        <a href="index.php?controller=PuntoVenta&action=crear" class="btn btn-primary">Nuevo punto de venta</a>
    </div>
    <table class="table table-striped">
        <thead>
            <tr>
                <th>Nombre</th>
                <th>Código</th>
                <th>Sucursal</th>
                <th>Estado</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($puntosVenta as $pv): ?>
            <tr>
                <td><?php echo htmlspecialchars($pv['nombre']); ?></td>
                <td><?php echo htmlspecialchars($pv['codigo']); ?></td>
                <td><?php echo htmlspecialchars($pv['sucursal_nombre']); ?></td>
                <td><?php echo !empty($pv['activo']) ? 'Activo' : 'Inactivo'; ?></td>
                <td>
                    <a href="index.php?controller=PuntoVenta&action=editar&id=<?php echo $pv['id']; ?>" class="btn btn-sm btn-warning">Editar</a>
                    <a href="index.php?controller=PuntoVenta&action=eliminar&id=<?php echo $pv['id']; ?>" class="btn btn-sm btn-danger" onclick="return confirm('¿Eliminar punto de venta?');">Eliminar</a>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
