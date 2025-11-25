<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h3>Depósitos</h3>
        <a href="index.php?controller=Deposito&action=crear" class="btn btn-primary">Nuevo depósito</a>
    </div>
    <table class="table table-striped">
        <thead>
            <tr>
                <th>Nombre</th>
                <th>Descripción</th>
                <th>Sucursal</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($depositos as $d): ?>
            <tr>
                <td><?php echo htmlspecialchars($d['nombre']); ?></td>
                <td><?php echo htmlspecialchars($d['descripcion']); ?></td>
                <td><?php echo htmlspecialchars($d['sucursal_nombre']); ?></td>
                <td>
                    <a href="index.php?controller=Deposito&action=editar&id=<?php echo $d['id']; ?>" class="btn btn-sm btn-warning" aria-label="Editar">
                        <i class="fa-solid fa-pen-to-square" aria-hidden="true"></i>
                        <span class="visually-hidden">Editar</span>
                    </a>
                    <a href="index.php?controller=Deposito&action=eliminar&id=<?php echo $d['id']; ?>" class="btn btn-sm btn-danger" onclick="return confirm('¿Eliminar depósito?');" aria-label="Eliminar">
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
