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
    <div class="login-logo">
        <img src="public/favicon.png" class="icono-login">
        <span class="textologin">
           Conta<strong>libra</strong>
        </span>
    </div>

    <h4 class="text-center mb-3">Cambia tu contraseña</h4>
    <p class="text-muted text-center">Por seguridad debes actualizar la contraseña antes de continuar.</p>

    <?php if (!empty($error)): ?>
        <div class="alert alert-danger text-center"><?php echo htmlspecialchars($error); ?></div>
    <?php endif; ?>

    <form method="post" action="index.php?controller=Auth&action=forzarCambioPassword">
        <div class="mb-3">
            <label class="form-label">Nueva contraseña</label>
            <input type="password" name="nueva" class="form-control" required autofocus>
        </div>
        <div class="mb-3">
            <label class="form-label">Confirmación</label>
            <input type="password" name="confirmacion" class="form-control" required>
        </div>

        <button class="btn btn-primary w-100 mt-3">Guardar y continuar</button>
    </form>
</div>

<?php include __DIR__ . '/../layout/footer.php'; ?>
