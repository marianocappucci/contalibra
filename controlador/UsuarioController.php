<?php
require_once "libs/log_helper.php";
class UsuarioController {

    private $model;

    public function __construct(){
    registrarLog("Acceso a __construct","Usuario");
        $this->model = new Usuario();
    }

    public function index(){
    registrarLog("Acceso a index","Usuario");
        $usuarios = $this->model->getAll();
        include __DIR__ . '/../vistas/usuarios/index.php';
    }

    public function crear(){
    registrarLog("Acceso a crear","Usuario");
        $roles = $this->model->getRoles();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            try {
                $this->model->create($this->prepareUserData($_POST));
                header('Location: index.php?controller=Usuario&action=index');
                exit;
            } catch (InvalidArgumentException $e) {
                $error = $e->getMessage();
            }
        }
        $usuario = null;
        include __DIR__ . '/../vistas/usuarios/form.php';
    }

    public function editar(){
    registrarLog("Acceso a editar","Usuario");
        $id = $_GET['id'] ?? null;
        if (!$id) { die('ID inválido'); }
        $roles = $this->model->getRoles();
        $usuario = $this->model->getById($id);
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            try {
                $this->model->update($id, $this->prepareUserData($_POST, $usuario));
                header('Location: index.php?controller=Usuario&action=index');
                exit;
            } catch (InvalidArgumentException $e) {
                $error = $e->getMessage();
            }
        }
        include __DIR__ . '/../vistas/usuarios/form.php';
    }

    public function eliminar(){
    registrarLog("Acceso a eliminar","Usuario");
        $id = $_GET['id'] ?? null;
        if ($id) {
            $this->model->delete($id);
        }
        header('Location: index.php?controller=Usuario&action=index');
        exit;
    }

    private function prepareUserData(array $data, ?array $originalUser = null): array
    {
        $dbName = '';
        if (isset($_SESSION['user']) && ($_SESSION['user']['rol_nombre'] ?? '') === 'Superusuario') {
            $dbName = $this->sanitizeDbName($data['base_datos'] ?? '');
            if ($dbName === '') {
                throw new InvalidArgumentException('Debes especificar una base de datos válida para el usuario.');
            }
        } else {
            $dbName = $_SESSION['user']['base_datos'] ?? ($originalUser['base_datos'] ?? '');
            if ($dbName === '') {
                throw new InvalidArgumentException('No se pudo determinar la base de datos desde la sesión.');
            }
        }

        $data['base_datos'] = $dbName;

        $password = $data['password'] ?? '';
        if ($password === '' && $originalUser) {
            $password = $originalUser['password'] ?? '';
        } else if ($password !== '') {
            $info = password_get_info($password);
            if (($info['algo'] ?? 0) === 0) {
                $password = password_hash($password, PASSWORD_BCRYPT);
            }
        }

        $data['password'] = $password;
        $data['activo'] = isset($data['activo']) ? 1 : 0;

        return $data;
    }

    private function sanitizeDbName(string $dbName): string
    {
        $clean = preg_replace('/[^a-zA-Z0-9_]/', '', trim($dbName));
        return $clean;
    }
}
