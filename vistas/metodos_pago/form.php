<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <h3><?php echo $metodo ? 'Editar método de pago' : 'Nuevo método de pago'; ?></h3>
    <form method="post">
        <div class="row">
            <div class="col-md-6 mb-3">
                <label class="form-label">Nombre</label>
                <input type="text" name="nombre" class="form-control" required value="<?php echo $metodo['nombre'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Descripción</label>
                <input type="text" name="descripcion" class="form-control" value="<?php echo $metodo['descripcion'] ?? ''; ?>">
            </div>
        </div>
        <button class="btn btn-success">Guardar</button>
        <a href="index.php?controller=MetodoPago&action=index" class="btn btn-secondary">Volver</a>
    </form>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
