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

            if ($user && $this->passwordMatches($password, $user)) {
                $dbName = $user['base_datos'] ?? DB_NAME;
                Database::setActiveDatabase($dbName);
                $_SESSION['user'] = [
                    'id' => $user['id'],
                    'nombre' => $user['nombre'],
                    'rol_id' => $user['rol_id'],
                    'rol_nombre' => $user['rol_nombre'],
                    'base_datos' => $dbName,
                ];
                header('Location: index.php?controller=Dashboard&action=index');
                exit;
            } else {
                $error = 'Usuario o contraseña incorrectos';
            }
        }
        include __DIR__ . '/../vistas/auth/login.php';
    }

    private function passwordMatches(string $plainPassword, array $user): bool
    {
        // Preferimos hash seguro; si detectamos una contraseña legacy plana la re-hasheamos tras el login.
        if (!empty($user['password']) && password_verify($plainPassword, $user['password'])) {
            return true;
        }

        if (!empty($user['password']) && hash_equals($user['password'], $plainPassword)) {
            $hashed = password_hash($plainPassword, PASSWORD_BCRYPT);
            (new Usuario())->updatePassword($user['id'], $hashed);
            return true;
        }

        return false;
    }

    public function logout(){
        registrarLog("Acceso a logout","Auth");
        session_destroy();
        header('Location: index.php');
        exit;
    }
}
