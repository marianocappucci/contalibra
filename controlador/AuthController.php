<?php
require_once "libs/log_helper.php";
class AuthController {

    public function login(){
    registrarLog("Acceso a login","Auth");
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $username = $_POST['username'] ?? '';
            $password = $_POST['password'] ?? '';

            $usuarioModel = new Usuario();
            $user = $usuarioModel->getByUsername($username);

            if ($user && $user['password'] === $password) { // demo: sin hash
                $_SESSION['user'] = [
                    'id' => $user['id'],
                    'nombre' => $user['nombre'],
                    'rol_id' => $user['rol_id'],
                    'rol_nombre' => $user['rol_nombre']
                ];
                header('Location: index.php?controller=Dashboard&action=index');
                exit;
            } else {
                $error = 'Usuario o contraseña incorrectos';
            }
        }
        include __DIR__ . '/../vistas/auth/login.php';
    }

    public function logout(){
    registrarLog("Acceso a logout","Auth");
        session_destroy();
        header('Location: index.php');
        exit;
    }
}
