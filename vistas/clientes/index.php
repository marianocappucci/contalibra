<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h3>Clientes</h3>
        <a href="index.php?controller=Cliente&action=crear" class="btn btn-primary">Nuevo cliente</a>
    </div>
    <table class="table table-striped">
        <thead>
            <tr>
                <th>Nombre</th>
                <th>Tipo</th>
                <th>Documento</th>
                <th>Email</th>
                <th>Saldo</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($clientes as $c): ?>
            <tr>
                <td><?php echo htmlspecialchars($c['nombre']); ?></td>
                <td><?php echo htmlspecialchars($c['tipo']); ?></td>
                <td><?php echo htmlspecialchars($c['documento']); ?></td>
                <td><?php echo htmlspecialchars($c['email']); ?></td>
                <td>$<?php echo number_format($c['saldo'], 2); ?></td>
                <td>
                    <a href="index.php?controller=Cliente&action=editar&id=<?php echo $c['id']; ?>" class="btn btn-sm btn-warning" aria-label="Editar">
                        <i class="fa-solid fa-pen-to-square" aria-hidden="true"></i>
                        <span class="visually-hidden">Editar</span>
                    </a>
                    <a href="index.php?controller=Cliente&action=eliminar&id=<?php echo $c['id']; ?>" class="btn btn-sm btn-danger" onclick="return confirm('¿Eliminar cliente?');" aria-label="Eliminar">
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
