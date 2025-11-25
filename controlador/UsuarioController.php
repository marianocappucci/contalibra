<?php
require_once "libs/log_helper.php";
require_once __DIR__ . '/../libs/TenantContext.php';
class UsuarioController {

    private $model;

    public function __construct(){
    registrarLog("Acceso a __construct","Usuario");
        $this->model = new Usuario();
    }

    public function index(){
    registrarLog("Acceso a index","Usuario");
        $empresaBase = $_SESSION['empresa_base'] ?? ($_SESSION['user']['base_datos'] ?? null);

        if (!empty($empresaBase)) {
            $usuarios = $this->model->getAllByBaseDatos($empresaBase);
        } else {
            $usuarios = [];
        }
        include __DIR__ . '/../vistas/usuarios/index.php';
    }

    public function crear(){
    registrarLog("Acceso a crear","Usuario");
        $roles = $this->model->getRoles();
        $basesDatos = $this->getAvailableDatabases();
        $error = '';
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            try {
                $this->model->create($this->prepareUserData($_POST, null, $basesDatos));
                header('Location: index.php?controller=Usuario&action=index');
                exit;
            } catch (InvalidArgumentException $e) {
                $error = $e->getMessage();
            } catch (PDOException $e) {
                $error = 'No se pudo crear el usuario. Verifica que el nombre de usuario sea único.';
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
        $basesDatos = $this->getAvailableDatabases($usuario['base_datos'] ?? null);
        $error = '';
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            try {
                $this->model->update($id, $this->prepareUserData($_POST, $usuario, $basesDatos));
                header('Location: index.php?controller=Usuario&action=index');
                exit;
            } catch (InvalidArgumentException $e) {
                $error = $e->getMessage();
            } catch (PDOException $e) {
                $error = 'No se pudo actualizar el usuario. Verifica que el nombre de usuario sea único.';
            }
        }
        include __DIR__ . '/../vistas/usuarios/form.php';
    }

    public function eliminar(){
    registrarLog("Acceso a eliminar","Usuario");
        $id = $_GET['id'] ?? null;
        $error = '';

        if ($id) {
            try {
                $this->model->delete((int) $id);
            } catch (RuntimeException $e) {
                $error = $e->getMessage();
            } catch (PDOException $e) {
                $error = 'No se pudo eliminar el usuario. Verifique que no tenga datos asociados.';
            }
        }

        $queryParams = [
            'controller' => 'Usuario',
            'action' => 'index'
        ];

        if ($error !== '') {
            $queryParams['error'] = $error;
        }

        header('Location: index.php?' . http_build_query($queryParams));
        exit;
    }

    private function prepareUserData(array $data, ?array $originalUser = null, array $availableDatabases = []): array
    {
        $dbName = '';
        if ($originalUser === null) {
            $dbName = $this->sanitizeDbName(TenantContext::activeDatabaseName());
            if ($dbName === '') {
                throw new InvalidArgumentException('No se pudo determinar la base de datos activa para el usuario.');
            }
            if (!empty($availableDatabases) && !in_array($dbName, $availableDatabases, true)) {
                throw new InvalidArgumentException('La base de datos activa no es válida para la creación de usuarios.');
            }
        } elseif (isset($_SESSION['user']) && ($_SESSION['user']['rol_nombre'] ?? '') === 'Superusuario') {
            $dbName = $this->sanitizeDbName($data['base_datos'] ?? '');
            if ($dbName === '') {
                throw new InvalidArgumentException('Debes especificar una base de datos válida para el usuario.');
            }
            if (!in_array($dbName, $availableDatabases, true)) {
                throw new InvalidArgumentException('Debes seleccionar una base de datos existente.');
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

    private function getAvailableDatabases(?string $includeDb = null): array
    {
        $empresaModel = new Empresa();
        $empresas = $empresaModel->getAll();
        $bases = [];

        foreach ($empresas as $empresa) {
            $dbName = $this->sanitizeDbName($empresa['base_datos'] ?? '');
            if ($dbName !== '') {
                $bases[$dbName] = $dbName;
            }
        }

        if ($includeDb !== null) {
            $bases[$includeDb] = $includeDb;
        }

        return array_values($bases);
    }
}
