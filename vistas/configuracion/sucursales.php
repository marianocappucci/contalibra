<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">
<div class="container">
    <h3>Sucursales</h3>

    <?php if (!empty($mensaje)): ?>
        <div class="alert alert-success"><?php echo htmlspecialchars($mensaje); ?></div>
    <?php endif; ?>

    <?php if (!empty($error)): ?>
        <div class="alert alert-danger"><?php echo htmlspecialchars($error); ?></div>
    <?php endif; ?>

    <div class="card mb-4">
        <div class="card-header">Crear nueva sucursal</div>
        <div class="card-body">
            <form method="post" class="row g-3">
                <div class="col-md-6">
                    <label class="form-label">Nombre *</label>
                    <input type="text" name="nombre" class="form-control" required value="<?php echo htmlspecialchars($_POST['nombre'] ?? ''); ?>">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Empresa *</label>
                    <select name="empresa_id" class="form-select" required>
                        <option value="">Selecciona una empresa</option>
                        <?php foreach ($empresas as $empresa): ?>
                            <option value="<?php echo (int) $empresa['id']; ?>" <?php echo ((int)($_POST['empresa_id'] ?? 0) === (int) $empresa['id']) ? 'selected' : ''; ?>>
                                <?php echo htmlspecialchars($empresa['nombre']); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Dirección</label>
                    <input type="text" name="direccion" class="form-control" value="<?php echo htmlspecialchars($_POST['direccion'] ?? ''); ?>">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Ciudad</label>
                    <input type="text" name="ciudad" class="form-control" value="<?php echo htmlspecialchars($_POST['ciudad'] ?? ''); ?>">
                </div>
                <div class="col-12">
                    <button class="btn btn-primary">Crear sucursal</button>
                    <a href="index.php?controller=Dashboard&action=index" class="btn btn-secondary">Volver</a>
                </div>
            </form>
        </div>
    </div>

    <div class="card">
        <div class="card-header">Sucursales registradas</div>
        <div class="card-body">
            <?php if (empty($sucursales)): ?>
                <p class="mb-0">Todavía no hay sucursales cargadas.</p>
            <?php else: ?>
                <div class="table-responsive">
                    <table class="table table-striped align-middle">
                        <thead>
                            <tr>
                                <th>Nombre</th>
                                <th>Empresa</th>
                                <th>Dirección</th>
                                <th>Ciudad</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($sucursales as $s): ?>
                                <tr>
                                    <td><?php echo htmlspecialchars($s['nombre']); ?></td>
                                    <td><?php echo htmlspecialchars($s['empresa_nombre'] ?? ''); ?></td>
                                    <td><?php echo htmlspecialchars($s['direccion']); ?></td>
                                    <td><?php echo htmlspecialchars($s['ciudad']); ?></td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            <?php endif; ?>
        </div>
    </div>
</div>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
