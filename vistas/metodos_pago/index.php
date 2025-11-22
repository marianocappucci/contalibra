<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h3>Métodos de pago</h3>
        <a href="index.php?controller=MetodoPago&action=crear" class="btn btn-primary">Nuevo método</a>
    </div>
    <table class="table table-striped">
        <thead>
            <tr>
                <th>Nombre</th>
                <th>Descripción</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($metodos as $m): ?>
            <tr>
                <td><?php echo htmlspecialchars($m['nombre']); ?></td>
                <td><?php echo htmlspecialchars($m['descripcion']); ?></td>
                <td>
                    <a href="index.php?controller=MetodoPago&action=editar&id=<?php echo $m['id']; ?>" class="btn btn-sm btn-warning">Editar</a>
                    <a href="index.php?controller=MetodoPago&action=eliminar&id=<?php echo $m['id']; ?>" class="btn btn-sm btn-danger" onclick="return confirm('¿Eliminar método?');">Eliminar</a>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
