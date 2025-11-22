<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <h3>Crear base de datos para nuevo comercio</h3>
    <?php if (!empty($mensaje)): ?>
        <div class="alert alert-success"><?php echo htmlspecialchars($mensaje); ?></div>
    <?php endif; ?>
    <?php if (!empty($error)): ?>
        <div class="alert alert-danger"><?php echo htmlspecialchars($error); ?></div>
    <?php endif; ?>
    <form method="post">
        <div class="mb-3">
            <label class="form-label">Nombre de la base</label>
            <input type="text" name="nombre_bd" class="form-control" required placeholder="contadb_demo">
            <div class="form-text">Solo se aceptan letras, números y guiones bajos.</div>
        </div>
        <button class="btn btn-success">Crear base en blanco</button>
    </form>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
