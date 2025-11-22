<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <h3><?php echo $proveedor ? 'Editar proveedor' : 'Nuevo proveedor'; ?></h3>
    <form method="post">
        <div class="row">
            <div class="col-md-6 mb-3">
                <label class="form-label">Nombre</label>
                <input type="text" name="nombre" class="form-control" required value="<?php echo $proveedor['nombre'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Contacto</label>
                <input type="text" name="contacto" class="form-control" value="<?php echo $proveedor['contacto'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Teléfono</label>
                <input type="text" name="telefono" class="form-control" value="<?php echo $proveedor['telefono'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-control" value="<?php echo $proveedor['email'] ?? ''; ?>">
            </div>
        </div>
        <button class="btn btn-success">Guardar</button>
        <a href="index.php?controller=Proveedor&action=index" class="btn btn-secondary">Volver</a>
    </form>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
