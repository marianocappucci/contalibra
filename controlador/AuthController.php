<?php
require_once "libs/log_helper.php";
class AuthController {

    public function login(){
        registrarLog("Acceso a login","Auth");
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $username = $_POST['username'] ?? '';
            $password = $_POST['password'] ?? '';
            $dbName = $this->sanitizeDbName($_POST['db_name'] ?? ($_SESSION['db_name'] ?? DB_NAME));

            Database::setActiveDatabase($dbName);

            $usuarioModel = new Usuario();
            $user = $usuarioModel->getByUsername($username);

            if ($user && $this->passwordMatches($password, $user)) {
                $dbName = $this->sanitizeDbName($user['base_datos'] ?? $dbName);
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

    public function cambiarEmpresa()
    {
        registrarLog("Acceso a cambiarEmpresa","Auth");

        if (!isset($_SESSION['user'])) {
            header('Location: index.php?controller=Auth&action=login');
            exit;
        }

        $dbName = $this->sanitizeDbName($_POST['db_name'] ?? ($_SESSION['db_name'] ?? DB_NAME));

        Database::setActiveDatabase($dbName);
        $_SESSION['user']['base_datos'] = $dbName;

        $redirect = $_SERVER['HTTP_REFERER'] ?? 'index.php?controller=Dashboard&action=index';
        header('Location: ' . $redirect);
        exit;
    }

    private function sanitizeDbName(string $dbName): string
    {
        $clean = preg_replace('/[^a-zA-Z0-9_]/', '', $dbName);
        return $clean ?: DB_NAME;
    }
}
