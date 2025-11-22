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
        <div class="dropdown">
            <a class="btn btn-outline-light btn-sm dropdown-toggle d-flex align-items-center gap-2" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                <span class="rounded-circle bg-secondary text-white d-inline-flex align-items-center justify-content-center" style="width: 32px; height: 32px;">
                    <i class="bi bi-person-fill"></i>
                </span>
                <div class="text-start">
                    <div class="fw-semibold small"><?php echo htmlspecialchars($_SESSION['user']['nombre']); ?></div>
                    <div class="text-white-50 small"><?php echo htmlspecialchars($_SESSION['user']['rol_nombre']); ?></div>
                </div>
            </a>
            <ul class="dropdown-menu dropdown-menu-end dropdown-menu-dark shadow">
               
                <li>
                    <a class="dropdown-item" href="index.php?controller=Auth&action=logout">
                        <i class="bi bi-box-arrow-right me-2"></i>
                        Cerrar sesión
                    </a>
                </li>
            </ul>
        </div>
    </div>

</nav>
