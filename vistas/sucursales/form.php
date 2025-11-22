<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <h3><?php echo $sucursal ? 'Editar sucursal' : 'Nueva sucursal'; ?></h3>
    <form method="post">
        <div class="row">
            <div class="col-md-6 mb-3">
                <label class="form-label">Nombre</label>
                <input type="text" name="nombre" class="form-control" required value="<?php echo $sucursal['nombre'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Dirección</label>
                <input type="text" name="direccion" class="form-control" value="<?php echo $sucursal['direccion'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Ciudad</label>
                <input type="text" name="ciudad" class="form-control" value="<?php echo $sucursal['ciudad'] ?? ''; ?>">
            </div>
        </div>
        <button class="btn btn-success">Guardar</button>
        <a href="index.php?controller=Sucursal&action=index" class="btn btn-secondary">Volver</a>
    </form>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
