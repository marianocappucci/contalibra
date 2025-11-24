<?php
chdir(__DIR__);
session_start();

// Stubs para evitar conexiones reales a BD y logs.
require_once __DIR__ . '/libs/log_helper.php';

class StubCaja
{
    public array $lastData = [];

    public function abrirCaja(array $data)
    {
        $this->lastData = $data;
        return true;
    }
}

class StubUsuario
{
    private ?array $defaultUser;
    private ?array $tenantUser;
    public bool $syncCalled = false;
    public bool $syncShouldFail = false;
    public ?array $syncedUser = null;

    public function __construct(?array $defaultUser, ?array $tenantUser = null)
    {
        $this->defaultUser = $defaultUser;
        $this->tenantUser = $tenantUser;
    }

    public function getByIdFromDefault(int $id)
    {
        return $this->defaultUser && $this->defaultUser['id'] === $id
            ? $this->defaultUser
            : null;
    }

    public function getById(int $id)
    {
        return $this->tenantUser && $this->tenantUser['id'] === $id
            ? $this->tenantUser
            : null;
    }

    public function syncFromMaster(array $usuarioMaestro)
    {
        $this->syncCalled = true;
        $this->syncedUser = $usuarioMaestro;

        if ($this->syncShouldFail) {
            return false;
        }

        $this->tenantUser = $usuarioMaestro;
        return true;
    }
}

require_once __DIR__ . '/../controlador/CajaController.php';

class CajaControllerTestDouble extends CajaController
{
    public function __construct($cajaModel, $usuarioModel)
    {
        parent::__construct($cajaModel, $usuarioModel);
    }

    public function procesar(array $payload): array
    {
        return $this->procesarApertura($payload);
    }
}

function assertTrue($condition, string $message)
{
    if (!$condition) {
        throw new RuntimeException($message);
    }
}

// Caso 1: el usuario existe en contadb y se sincroniza en la base del tenant.
$_SESSION['user'] = ['id' => 7, 'nombre' => 'Master User'];
$cajaModel = new StubCaja();
$usuarioModel = new StubUsuario(['id' => 7, 'nombre' => 'Master User']);
$controller = new CajaControllerTestDouble($cajaModel, $usuarioModel);

$resultado = $controller->procesar([
    'nombre' => 'Caja de prueba',
    'saldo_inicial' => 123.45,
]);

assertTrue($resultado['ok'] === true, 'La apertura debe ser exitosa cuando el usuario está en la base maestra.');
assertTrue($usuarioModel->syncCalled === true, 'Debe intentarse sincronizar el usuario en la base del tenant.');
assertTrue($cajaModel->lastData['usuario_id'] === 7, 'La apertura debe usar el ID del usuario autenticado.');
assertTrue($cajaModel->lastData['nombre'] === 'Caja de prueba', 'Debe enviarse el nombre de la caja.');

// Caso 2: el usuario existe en el tenant y no requiere sincronización.
$_SESSION['user'] = ['id' => 8, 'nombre' => 'Tenant User'];
$cajaModel = new StubCaja();
$usuarioModel = new StubUsuario(['id' => 8, 'nombre' => 'Tenant User'], ['id' => 8, 'nombre' => 'Tenant User']);
$controller = new CajaControllerTestDouble($cajaModel, $usuarioModel);

$resultado = $controller->procesar([
    'nombre' => 'Caja existente',
    'saldo_inicial' => 50,
]);

assertTrue($resultado['ok'] === true, 'La apertura debe ser exitosa cuando el usuario ya existe en el tenant.');
assertTrue($usuarioModel->syncCalled === false, 'No debe sincronizarse el usuario si ya existe en el tenant.');
assertTrue($cajaModel->lastData['usuario_id'] === 8, 'Debe usarse el ID del usuario del tenant.');

// Caso 3: el usuario no existe ni en sesión ni en la base maestra.
$_SESSION['user'] = null;
$cajaModel = new StubCaja();
$usuarioModel = new StubUsuario(null);
$controller = new CajaControllerTestDouble($cajaModel, $usuarioModel);
$resultado = $controller->procesar([
    'nombre' => 'Caja sin usuario',
    'saldo_inicial' => 10,
]);

assertTrue($resultado['ok'] === false, 'La apertura debe fallar sin usuario autenticado.');
assertTrue(stripos($resultado['error'], 'Usuario') !== false, 'El mensaje debe indicar el problema con el usuario.');

// Caso 4: el usuario existe en la base maestra pero falla la sincronización en el tenant.
$_SESSION['user'] = ['id' => 9, 'nombre' => 'Usuario sin sincronizar'];
$cajaModel = new StubCaja();
$usuarioModel = new StubUsuario(['id' => 9, 'nombre' => 'Usuario sin sincronizar']);
$usuarioModel->syncShouldFail = true;
$controller = new CajaControllerTestDouble($cajaModel, $usuarioModel);

$resultado = $controller->procesar([
    'nombre' => 'Caja con fallo de sync',
    'saldo_inicial' => 20,
]);

assertTrue($resultado['ok'] === false, 'La apertura debe fallar si no se puede sincronizar el usuario.');
assertTrue(stripos($resultado['error'], 'sincronizar') !== false, 'El mensaje debe advertir sobre la sincronización fallida.');

fwrite(STDOUT, "CajaControllerTest: ok\n");
