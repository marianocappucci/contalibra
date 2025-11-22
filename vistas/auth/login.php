<?php include __DIR__ . '/../layout/header.php'; ?>

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">

<style>
    body {
        background: #f0f2f5;
    }

    .login-container {
        max-width: 420px;
        margin: 90px auto;
        background: white;
        padding: 35px 30px;
        border-radius: 10px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.15);
    }

    .login-logo {
        font-size: 2rem;
        font-weight: bold;
        color: #0d6efd;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        margin-bottom: 20px;
    }

    .login-logo i {
        font-size: 2.4rem;
    }
</style>

<div class="login-container">

    <!-- LOGO CONTALIBRA EN LOGIN -->
    <div class="login-logo">
        <img src="public/favicon.png" class="icono-login">
        <span class="textologin">
           Conta<strong>libra</strong>
        </span>
    </div>

    <h4 class="text-center mb-4">Iniciar Sesión</h4>

    <?php if (!empty($error)): ?>
        <div class="alert alert-danger text-center"><?php echo $error; ?></div>
    <?php endif; ?>

    <form method="post" action="index.php?controller=Auth&action=login">
        <div class="mb-3">
            <label class="form-label">Empresa / Base de datos</label>
            <input type="text" name="db_name" class="form-control" placeholder="contadb_empresa"
                   value="<?php echo htmlspecialchars($_SESSION['db_name'] ?? DB_NAME); ?>" required>
            <small class="text-muted">Usaremos esta base para validar tus datos.</small>
        </div>

        <div class="mb-3">
            <label class="form-label">Usuario</label>
            <input type="text" name="username" class="form-control" required autofocus>
        </div>

        <div class="mb-3">
            <label class="form-label">Contraseña</label>
            <input type="password" name="password" class="form-control" required>
        </div>

        <button class="btn btn-primary w-100 mt-3">Ingresar</button>
    </form>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
