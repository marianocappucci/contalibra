<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h3>Proveedores</h3>
        <a href="index.php?controller=Proveedor&action=crear" class="btn btn-primary">Nuevo proveedor</a>
    </div>
    <table class="table table-striped">
        <thead>
            <tr>
                <th>Nombre</th>
                <th>Contacto</th>
                <th>Teléfono</th>
                <th>Email</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($proveedores as $p): ?>
            <tr>
                <td><?php echo htmlspecialchars($p['nombre']); ?></td>
                <td><?php echo htmlspecialchars($p['contacto']); ?></td>
                <td><?php echo htmlspecialchars($p['telefono']); ?></td>
                <td><?php echo htmlspecialchars($p['email']); ?></td>
                <td>
                    <a href="index.php?controller=Proveedor&action=editar&id=<?php echo $p['id']; ?>" class="btn btn-sm btn-warning" aria-label="Editar">
                        <i class="fa-solid fa-pen-to-square" aria-hidden="true"></i>
                        <span class="visually-hidden">Editar</span>
                    </a>
                    <a href="index.php?controller=Proveedor&action=eliminar&id=<?php echo $p['id']; ?>" class="btn btn-sm btn-danger" onclick="return confirm('¿Eliminar proveedor?');" aria-label="Eliminar">
                        <i class="fa-solid fa-trash" aria-hidden="true"></i>
                        <span class="visually-hidden">Eliminar</span>
                    </a>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
