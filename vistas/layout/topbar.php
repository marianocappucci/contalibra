<nav class="navbar navbar-expand-lg navbar-dark bg-dark px-4" 
     style="height: 60px; position: fixed; top: 0; left: 0; width: 100%; z-index: 1000;">

    <div class="d-flex align-items-center">
        <img src="public/favicon.png" class="icono-menu">

       

        <span class="navbar-brand mb-0 h1 fw-bold fs-4">
           Conta<strong>libra</strong>
        </span>
    </div>

    <div class="ms-auto d-flex align-items-center">

        <form class="d-flex align-items-center me-3" method="post" action="index.php?controller=Auth&action=cambiarEmpresa">
            <label class="text-white me-2 mb-0">Empresa</label>
            <input type="text" name="db_name" class="form-control form-control-sm"
                   value="<?php echo htmlspecialchars($_SESSION['user']['base_datos'] ?? ($_SESSION['db_name'] ?? DB_NAME)); ?>"
                   style="max-width: 180px;">
            <button class="btn btn-outline-light btn-sm ms-2" type="submit">Cambiar</button>
        </form>

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
