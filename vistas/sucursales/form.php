<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <h3><?php echo $sucursal ? 'Editar sucursal' : 'Nueva sucursal'; ?></h3>
    <?php if (!empty($error)): ?>
        <div class="alert alert-danger"><?php echo htmlspecialchars($error); ?></div>
    <?php endif; ?>
    <form method="post">
        <?php
            $empresas = $empresas ?? [];
            $empresaActiva = $empresaActiva ?? [];
            $esEdicion = $sucursal !== null;
            $empresaSeleccionada = $_POST['empresa_id'] ?? ($sucursal['empresa_id'] ?? '');
            $empresaActivaNombre = $empresaActiva['nombre'] ?? 'Sin empresa activa';
        ?>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label class="form-label">Nombre</label>
                <input type="text" name="nombre" class="form-control" required value="<?php echo htmlspecialchars($sucursal['nombre'] ?? ''); ?>">
            </div>
            <div class="col-md-6 mb-3">
                <label class="form-label">Dirección</label>
                <input type="text" name="direccion" class="form-control" value="<?php echo htmlspecialchars($sucursal['direccion'] ?? ''); ?>">
            </div>
            <?php if ($esEdicion): ?>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Empresa</label>
                    <select name="empresa_id" class="form-select">
                        <option value="">Sin empresa</option>
                        <?php foreach ($empresas as $empresa): ?>
                            <option value="<?php echo (int) $empresa['id']; ?>" <?php echo ((string) $empresaSeleccionada === (string) $empresa['id']) ? 'selected' : ''; ?>>
                                <?php echo htmlspecialchars($empresa['nombre']); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>
            <?php else: ?>
                <div class="col-md-6 mb-3">
                    <label class="form-label">Empresa activa</label>
                    <input type="hidden" name="empresa_id" value="<?php echo htmlspecialchars($empresaActiva['id'] ?? ''); ?>">
                    <input type="text" class="form-control" value="<?php echo htmlspecialchars($empresaActivaNombre); ?>" readonly>
                </div>
            <?php endif; ?>
            <div class="col-md-6 mb-3">
                <label class="form-label">Ciudad</label>
                <input type="text" name="ciudad" class="form-control" value="<?php echo htmlspecialchars($sucursal['ciudad'] ?? ''); ?>">
            </div>
        </div>
        <button class="btn btn-success">Guardar</button>
        <a href="index.php?controller=Sucursal&action=index" class="btn btn-secondary">Volver</a>
    </form>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
