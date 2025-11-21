<nav class="navbar navbar-expand-lg navbar-dark bg-dark px-4" 
     style="height: 60px; position: fixed; top: 0; left: 0; width: 100%; z-index: 1000;">

    <div class="d-flex align-items-center">
        <i class="bi bi-layers-half text-white fs-3 me-2"></i>
       

        <span class="navbar-brand mb-0 h1 fw-bold fs-4">
            Contalibra
        </span>
    </div>

    <div class="ms-auto d-flex align-items-center">

        <!-- Dropdown de usuario -->
        <div class="dropdown">
            <a class="text-white fw-semibold dropdown-toggle text-decoration-none" 
               href="#" 
               id="userMenu" 
               data-bs-toggle="dropdown" 
               aria-expanded="false"
               style="cursor: pointer;">
                <?php echo htmlspecialchars($_SESSION['user']['nombre']); ?>
                (<?php echo htmlspecialchars($_SESSION['user']['rol_nombre']); ?>)
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
