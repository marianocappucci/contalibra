<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <h3><?php echo $puntoVenta ? 'Editar punto de venta' : 'Nuevo punto de venta'; ?></h3>
    <form method="post">
        <div class="row">
            <div class="col-md-6 mb-3">
                <label class="form-label">Nombre</label>
                <input type="text" name="nombre" class="form-control" required value="<?php echo $puntoVenta['nombre'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Código</label>
                <input type="text" name="codigo" class="form-control" value="<?php echo $puntoVenta['codigo'] ?? ''; ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Sucursal</label>
                <select name="sucursal_id" class="form-select" required>
                    <option value="">Selecciona una sucursal</option>
                    <?php foreach ($sucursales as $s): ?>
                        <option value="<?php echo $s['id']; ?>" <?php echo (($puntoVenta['sucursal_id'] ?? null) == $s['id']) ? 'selected' : ''; ?>><?php echo htmlspecialchars($s['nombre']); ?></option>
                    <?php endforeach; ?>
                </select>
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Estado</label>
                <select name="activo" class="form-select">
                    <option value="1" <?php echo (($puntoVenta['activo'] ?? 1) == 1) ? 'selected' : ''; ?>>Activo</option>
                    <option value="0" <?php echo (($puntoVenta['activo'] ?? 1) == 0) ? 'selected' : ''; ?>>Inactivo</option>
                </select>
            </div>
        </div>
        <button class="btn btn-success">Guardar</button>
        <a href="index.php?controller=PuntoVenta&action=index" class="btn btn-secondary">Volver</a>
    </form>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
