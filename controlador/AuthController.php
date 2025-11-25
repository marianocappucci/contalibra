<?php
require_once "libs/log_helper.php";

class AuthController {

    public function login(){
        $dbFallbackMessage = $_SESSION['db_fallback_message'] ?? null;

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {

            $username = $_POST['username'] ?? '';
            $password = $_POST['password'] ?? '';

            $usuarioModel = new Usuario();
            $dbNameFilter = $_POST['base_datos'] ?? ($_SESSION['db_name'] ?? null);
            $users = $usuarioModel->findActiveByUsername($username, $dbNameFilter);

            $user = null;
            foreach ($users as $candidate) {
                if ($this->passwordMatches($password, $candidate)) {
                    $user = $candidate;
                    break;
                }
            }

            // ¿Usuario encontrado?
            if ($user) {

                // Asignar base de datos automáticamente si está vacía
                if (empty($user['base_datos'])) {

                    $dbName = "contadb";

                    $stmt = $usuarioModel->db->prepare("UPDATE usuarios SET base_datos=? WHERE id=?");
                    $stmt->execute([$dbName, $user['id']]);

                    $user['base_datos'] = $dbName;
                }

                // Iniciar sesión
                session_start();
                $_SESSION['user'] = [
                    'id' => $user['id'],
                    'nombre' => $user['nombre'],
                    'username' => $user['username'],
                    'rol_id' => $user['rol_id'] ?? null,
                    'rol_nombre' => $user['rol_nombre'] ?? '',
                    'base_datos' => $user['base_datos'],
                ];
                $_SESSION['db_name'] = $user['base_datos'];

                // Registrar log AHORA (ya hay usuario válido)
                registrarLog("Acceso correcto", "Auth");

                header("Location: index.php?controller=Dashboard&action=index");
                exit;
            }

            // Si llegamos acá no pasó validación
            $error = "Usuario o contraseña incorrectos";
            require "vistas/auth/login.php";
            return;
        }

        // Mostrar login al principio
        require "vistas/auth/login.php";
    }

    private function passwordMatches($plainPassword, $user){
        // Caso contraseña hash
        if (!empty($user['password']) && password_verify($plainPassword, $user['password'])) {
            return true;
        }

        // Caso contraseña en texto plano (primera vez)
        if ($user['password'] === $plainPassword) {

            // Encriptar ahora
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

