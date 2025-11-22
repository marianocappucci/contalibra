<nav class="navbar navbar-expand-lg navbar-dark bg-dark px-4"
     style="height: 60px; position: fixed; top: 0; left: 0; width: 100%; z-index: 1000;">

    <?php
        $configuracion = null;
        $empresaActiva = null;
        $baseActiva = $_SESSION['db_name'] ?? ($_SESSION['user']['base_datos'] ?? null);

        try {
            $configuracionModel = new Configuracion();
            $configuracion = $configuracionModel->get();
            $empresaActiva = $configuracion['nombre_fantasia'] ?? null;
        } catch (Exception $e) {
            $empresaActiva = $baseActiva;
        }

        if ($empresaActiva === null) {
            $empresaActiva = $baseActiva;
        }

        $empresaActivaNombre = $empresaActiva ?? 'No configurada';
    ?>

    <div class="ms-auto d-flex align-items-center gap-3">
        <div class="text-white">
            <div class="fw-semibold">
                <?php echo htmlspecialchars($_SESSION['user']['nombre']); ?>
                (<?php echo htmlspecialchars($_SESSION['user']['rol_nombre']); ?>)
            </div>
            <small class="text-secondary">Empresa: <?php echo htmlspecialchars($empresaActivaNombre); ?></small>
        </div>

        <a class="btn btn-outline-light btn-sm" href="index.php?controller=Auth&action=logout">
            <i class="bi bi-box-arrow-right me-2"></i> Cerrar sesión
        </a>
    </div>

</nav>
