<?php
require_once "libs/log_helper.php";
class ConfiguracionController {

    private $model;

    public function __construct(){
    registrarLog("Acceso a __construct","Configuracion");
        $this->model = new Configuracion();
        if (!isset($_SESSION['user']) || !in_array($_SESSION['user']['rol_nombre'], ['Administrador', 'Superusuario'])) {
            die("Acceso denegado");
        }
    }

    public function index(){
    registrarLog("Acceso a index","Configuracion");
        $config = $this->model->get();
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->model->update($_POST);
            $config = $this->model->get();
            $mensaje = "Configuración actualizada correctamente";
        }
        include __DIR__ . '/../vistas/configuracion/index.php';
    }

    public function manejoBd()
    {
        registrarLog("Acceso a manejoBd","Configuracion");

        $this->ensureMasterSuperuser();

        $usuarios = (new Usuario())->getAll();

        $mensaje = null;
        $error = null;

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $dbName = $this->sanitizeDbName($_POST['nombre_bd'] ?? '');
            $empresaNombre = trim($_POST['empresa_nombre'] ?? '');
            $usuarioId = $_POST['usuario_id'] ?? '';

            if ($dbName === '') {
                $error = 'Debes indicar un nombre de base de datos válido (solo letras, números y guiones bajos).';
            } elseif ($empresaNombre === '') {
                $error = 'Debes indicar el nombre de la empresa asociada.';
            } else {
                try {
                    $pdoRoot = $this->crearBaseDatos($dbName);
                    $this->importarEstructuraBase($pdoRoot, $dbName);
                    $this->configurarNombreFantasia($pdoRoot, $dbName, $empresaNombre);

                    if ($usuarioId !== '') {
                        $this->asignarBaseAUsuario($usuarioId, $dbName);
                        $mensaje = "Base '$dbName' creada para la empresa '$empresaNombre' y asignada al usuario seleccionado.";
                    } else {
                        $mensaje = "Base '$dbName' creada para la empresa '$empresaNombre'. Puedes asignarla a un usuario cuando lo necesites.";
                    }
                } catch (Exception $e) {
                    $error = 'No se pudo crear la base: ' . $e->getMessage();
                }
            }
        }

        include __DIR__ . '/../vistas/configuracion/manejo_bd.php';
    }

    public function empresas()
    {
        registrarLog("Acceso a empresas","Configuracion");

        if ($_SESSION['user']['rol_nombre'] !== 'Superusuario') {
            die("Acceso denegado");
        }

        $empresaModel = new Empresa();
        $empresas = $empresaModel->getAll();
        $mensaje = null;
        $error = null;
        $dbPreview = '';

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $empresaNombre = trim($_POST['empresa_nombre'] ?? '');
            $dbName = $this->generarNombreBaseDatos($empresaNombre);

            $dbPreview = $dbName;

            if ($empresaNombre === '') {
                $error = 'Debes indicar el nombre de la empresa.';
            } elseif ($dbName === '') {
                $error = 'El nombre de la empresa debe generar un identificador válido para la base de datos.';
            } elseif ($empresaModel->getByBaseDatos($dbName)) {
                $error = 'Ya existe una empresa con la base de datos generada. Usa un nombre diferente.';
            } else {
                try {
                    $empresaId = $empresaModel->create([
                        'nombre' => $empresaNombre,
                        'base_datos' => $dbName,
                    ]);

                    $configuracion = new Configuracion(Database::getStandaloneConnection($dbName));
                    $configuracion->setNombreFantasia($empresaNombre);

                    $mensaje = "Empresa '$empresaNombre' creada con ID $empresaId y base '$dbName'.";
                    $empresas = $empresaModel->getAll();
                    $dbPreview = $dbName;
                } catch (Exception $e) {
                    $error = 'No se pudo crear la empresa: ' . $e->getMessage();
                }
            }
        }

        include __DIR__ . '/../vistas/configuracion/empresas.php';
    }

    public function sucursales()
    {
        registrarLog("Acceso a sucursales","Configuracion");

        $empresaModel = new Empresa();
        $empresaIdActiva = TenantContext::empresaId();

        if ($empresaIdActiva === null && isset($_SESSION['empresa_id'])) {
            $empresaIdActiva = (int) $_SESSION['empresa_id'];
        }

        if ($empresaIdActiva === null && isset($_SESSION['user']['empresa_id'])) {
            $empresaIdActiva = (int) $_SESSION['user']['empresa_id'];
        }

        $empresaActiva = $empresaIdActiva
            ? $empresaModel->getByIdFromDefault((int) $empresaIdActiva)
            : null;

        if ($empresaActiva === null && !empty($_SESSION['user']['base_datos'])) {
            $empresaActiva = $empresaModel->getByBaseDatos($_SESSION['user']['base_datos']);
            $empresaIdActiva = $empresaActiva ? (int) $empresaActiva['id'] : null;
        }

        $empresas = $empresaActiva ? [$empresaActiva] : [];

        $sucursalModel = new Sucursal(Database::getDefaultStandaloneConnection());
        $sucursales = $empresaActiva
            ? $sucursalModel->getAll((int) $empresaActiva['id'])
            : [];

        $mensaje = null;
        $error = $empresaActiva ? null : 'No hay una empresa activa seleccionada.';

        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $nombre = trim($_POST['nombre'] ?? '');
            $direccion = trim($_POST['direccion'] ?? '');
            $ciudad = trim($_POST['ciudad'] ?? '');

            if ($nombre === '') {
                $error = 'Debes indicar el nombre de la sucursal.';
            } elseif ($empresaActiva === null) {
                $error = 'No hay una empresa activa para asociar la sucursal.';
            } else {
                try {
                    $creada = $sucursalModel->create([
                        'nombre' => $nombre,
                        'direccion' => $direccion,
                        'ciudad' => $ciudad,
                        'empresa_id' => (int) $empresaActiva['id'],
                    ]);

                    if ($creada) {
                        $mensaje = 'Sucursal creada correctamente.';
                        $sucursales = $sucursalModel->getAll((int) $empresaActiva['id']);
                    }
                } catch (Throwable $e) {
                    $error = 'No se pudo crear la sucursal: ' . $e->getMessage();
                }
            }
        }

        include __DIR__ . '/../vistas/configuracion/sucursales.php';
    }

    private function sanitizeDbName(string $dbName): string
    {
        return preg_replace('/[^a-zA-Z0-9_]/', '', trim($dbName));
    }

    private function crearBaseDatos(string $dbName): PDO
    {
        $dsn = 'mysql:host=' . DB_HOST;
        $pdo = new PDO($dsn, DB_USER, DB_PASS, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::MYSQL_ATTR_MULTI_STATEMENTS => true,
        ]);

        $pdo->exec("CREATE DATABASE IF NOT EXISTS `$dbName` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci");
        return $pdo;
    }

    private function importarEstructuraBase(PDO $pdoRoot, string $dbName): void
    {
        $pdoDb = new PDO($pdoRoot->getAttribute(PDO::ATTR_DRIVER_NAME) . ':host=' . DB_HOST . ';dbname=' . $dbName . ';charset=utf8mb4', DB_USER, DB_PASS, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);

        $sqlFile = __DIR__ . '/../backup_temp.sql';
        if (!file_exists($sqlFile)) {
            throw new RuntimeException('No se encontró el archivo SQL: ' . $sqlFile);
        }

        $sql = file_get_contents($sqlFile);
        $statements = array_filter(array_map('trim', explode(";\n", $sql)));

        foreach ($statements as $statement) {
            if ($statement === '') {
                continue;
            }

            if (preg_match('/^\s*INSERT\s+INTO\s+`?usuarios`?/i', $statement)) {
                continue;
            }

            $pdoDb->exec($statement);
        }
    }

    private function configurarNombreFantasia(PDO $pdoRoot, string $dbName, string $empresaNombre): void
    {
        $pdoDb = new PDO($pdoRoot->getAttribute(PDO::ATTR_DRIVER_NAME) . ':host=' . DB_HOST . ';dbname=' . $dbName . ';charset=utf8mb4', DB_USER, DB_PASS, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);

        $stmt = $pdoDb->prepare('UPDATE configuracion SET nombre_fantasia=?, actualizado=NOW() WHERE id=1');
        $stmt->execute([$empresaNombre]);
    }

    private function actualizarDatosInicialesEmpresa(PDO $pdoRoot, string $dbName, int $empresaId, string $empresaNombre): void
    {
        $pdoDb = new PDO($pdoRoot->getAttribute(PDO::ATTR_DRIVER_NAME) . ':host=' . DB_HOST . ';dbname=' . $dbName . ';charset=utf8mb4', DB_USER, DB_PASS, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);

        $pdoDb->beginTransaction();
        try {
            $pdoDb->exec('SET FOREIGN_KEY_CHECKS=0');

            $stmt = $pdoDb->prepare('UPDATE empresas SET id=?, nombre=?, base_datos=? WHERE id=1');
            $stmt->execute([$empresaId, $empresaNombre, $dbName]);

            $stmt = $pdoDb->prepare('UPDATE usuarios SET empresa_id=?, base_datos=? WHERE empresa_id=1');
            $stmt->execute([$empresaId, $dbName]);

            $stmt = $pdoDb->prepare('UPDATE sucursales SET empresa_id=? WHERE empresa_id=1');
            $stmt->execute([$empresaId]);

            $pdoDb->exec('ALTER TABLE empresas AUTO_INCREMENT = ' . ($empresaId + 1));

            $pdoDb->exec('SET FOREIGN_KEY_CHECKS=1');
            $pdoDb->commit();
        } catch (Exception $e) {
            $pdoDb->rollBack();
            $pdoDb->exec('SET FOREIGN_KEY_CHECKS=1');
            throw $e;
        }
    }

    private function asignarBaseAUsuario(string $usuarioId, string $dbName): void
    {
        $usuarioModel = new Usuario();
        $resultado = $usuarioModel->asignarBaseDatos((int)$usuarioId, $dbName);

        if (!$resultado) {
            throw new RuntimeException('No se pudo asignar la base de datos al usuario.');
        }
    }

    private function generarNombreBaseDatos(string $empresaNombre): string
    {
        $normalizado = strtolower(trim($empresaNombre));
        $normalizado = preg_replace('/[^a-z0-9_]+/i', '_', $normalizado);
        $normalizado = trim($normalizado, '_');

        if ($normalizado === '') {
            return '';
        }

        return 'contadb_' . $normalizado;
    }

    private function ensureMasterSuperuser(): void
    {
        $user = $_SESSION['user'] ?? null;

        $activeDatabase = $_SESSION['db_name'] ?? ($user['base_datos'] ?? '');

        $isSuperuser = isset($user['rol_nombre']) && strcasecmp($user['rol_nombre'], 'Superusuario') === 0;
        $isMasterDatabase = strcasecmp($activeDatabase, DB_NAME) === 0;

        if (!$isSuperuser || !$isMasterDatabase) {
            die('Acceso denegado');
        }
    }
}
