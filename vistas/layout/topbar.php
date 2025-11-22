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

    <div class="ms-auto d-flex align-items-center">

        <!-- Dropdown de usuario -->
        <div class="dropdown">
            <a class="text-white dropdown-toggle text-decoration-none"
               href="#"
               id="userMenu"
               data-bs-toggle="dropdown"
               aria-expanded="false"
               style="cursor: pointer;">
                <div class="d-flex flex-column align-items-start">
                    <div class="fw-semibold">
                        <?php echo htmlspecialchars($_SESSION['user']['nombre']); ?>
                        (<?php echo htmlspecialchars($_SESSION['user']['rol_nombre']); ?>)
                    </div>
                    <small class="text-secondary">Empresa: <?php echo htmlspecialchars($empresaActivaNombre); ?></small>
                </div>
            </a>

            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="userMenu">

                <li>
                    <a class="dropdown-item" href="index.php?controller=Auth&action=logout">
                        <i class="bi bi-box-arrow-right me-2"></i> Cerrar sesión
                    </a>
                </li>

            </ul>
        </div>

    </div>

</nav>
