<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <h3><?php echo $cliente ? 'Editar cliente' : 'Nuevo cliente'; ?></h3>
    <form method="post">
        <div class="row">
            <div class="col-md-6 mb-3">
                <label class="form-label">Nombre</label>
                <input type="text" name="nombre" class="form-control" required value="<?php echo $cliente['nombre'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Tipo</label>
                <select name="tipo" class="form-select">
                    <?php $tipos = ['Consumidor Final','Responsable Inscripto','Monotributo','Exento']; ?>
                    <?php foreach ($tipos as $t): ?>
                        <option value="<?php echo $t; ?>" <?php echo (($cliente['tipo'] ?? '') === $t) ? 'selected' : ''; ?>><?php echo $t; ?></option>
                    <?php endforeach; ?>
                </select>
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Documento/CUIT</label>
                <input type="text" name="documento" class="form-control" value="<?php echo $cliente['documento'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-control" value="<?php echo $cliente['email'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Dirección</label>
                <input type="text" name="direccion" class="form-control" value="<?php echo $cliente['direccion'] ?? ''; ?>">
            </div>
            <div class="col-md-3 mb-3">
                <label class="form-label">Saldo (cuenta corriente)</label>
                <input type="number" step="0.01" name="saldo" class="form-control" value="<?php echo $cliente['saldo'] ?? '0'; ?>">
            </div>
        </div>
        <button class="btn btn-success">Guardar</button>
        <a href="index.php?controller=Cliente&action=index" class="btn btn-secondary">Volver</a>
    </form>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
