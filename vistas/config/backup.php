<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
    <div class="container-fluid nv-wrapper">



    <h3>Backup y Restauración</h3>
    <p class="text-muted">Administre resguardos de su base de datos Contalibra (contadb).</p>

    <?php if (isset($msg)): ?>
        <div class="alert alert-info"><?= $msg ?></div>
    <?php endif; ?>

    <div class="card p-3 mb-4">
        <h5>Generar backup</h5>
        <p>Descargue una copia completa de la base de datos.</p>
        <a href="index.php?controller=Backup&action=generar" class="btn btn-primary">
            Descargar backup
        </a>
    </div>

    <div class="card p-3">
        <h5>Restaurar base de datos</h5>
        <form method="post" enctype="multipart/form-data" action="index.php?controller=Backup&action=restaurar">
            <input type="file" class="form-control mb-2" name="archivo" accept=".sql" required>
            <button type="submit" class="btn btn-danger">Restaurar</button>
        </form>
    </div>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
