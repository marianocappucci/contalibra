<?php
require_once "libs/log_helper.php";
require_once __DIR__ . '/../libs/TenantContext.php';
require_once __DIR__ . '/../config/database.php';

class AuthController {

    public function login(){
        $dbFallbackMessage = $_SESSION['db_fallback_message'] ?? null;

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {

            $username = $_POST['username'] ?? '';
            $password = $_POST['password'] ?? '';

            $usuarioModel = new Usuario();
            // En el login no debemos restringir la búsqueda a la base que
            // pudiera estar guardada en la sesión (podría pertenecer a otro
            // tenant). Solo filtramos si el formulario envía explícitamente
            // una base de datos.
            $dbNameFilter = $_POST['base_datos'] ?? null;
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
                $baseDatos = $user['base_datos'];

                // Asignar base de datos automáticamente si está vacía
                if (empty($baseDatos)) {

                    $baseDatos = "contadb";

                    $stmt = $usuarioModel->db->prepare("UPDATE usuarios SET base_datos=? WHERE id=?");
                    $stmt->execute([$baseDatos, $user['id']]);

                    $user['base_datos'] = $baseDatos;
                }

                $empresaModel = new Empresa();
                $empresa = $empresaModel->getByBaseDatos($baseDatos);

                if (!$empresa) {
                    $error = "El usuario no está asociado a ninguna empresa configurada.";
                    require "vistas/auth/login.php";
                    return;
                }

                // Iniciar sesión
                session_start();
                $_SESSION['user'] = [
                    'id' => $user['id'],
                    'nombre' => $user['nombre'],
                    'username' => $user['username'],
                    'rol_id' => $user['rol_id'] ?? null,
                    'rol_nombre' => $user['rol_nombre'] ?? '',
                    'base_datos' => $baseDatos,
                    'empresa_id' => (int) $empresa['id'],
                ];
                $_SESSION['db_name'] = $baseDatos;
                $_SESSION['empresa_id'] = (int) $empresa['id'];
                $_SESSION['empresa_nombre'] = $empresa['nombre'];
                unset($_SESSION['sucursal_id'], $_SESSION['sucursal_nombre'], $_SESSION['punto_venta_id'], $_SESSION['punto_venta_nombre']);

                TenantContext::setContext((int) $empresa['id'], null);
                Database::setActiveDatabase($baseDatos);

                // Registrar log AHORA (ya hay usuario válido)
                registrarLog("Acceso correcto", "Auth");

                header("Location: index.php?controller=Contexto&action=seleccionar");
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

