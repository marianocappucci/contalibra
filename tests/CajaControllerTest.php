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

    public function __construct(?array $defaultUser)
    {
        $this->defaultUser = $defaultUser;
    }

    public function getByIdFromDefault(int $id)
    {
        return $this->defaultUser && $this->defaultUser['id'] === $id
            ? $this->defaultUser
            : null;
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

// Caso 1: el usuario existe en contadb aunque falte en la base del tenant.
$_SESSION['user'] = ['id' => 7, 'nombre' => 'Master User'];
$cajaModel = new StubCaja();
$usuarioModel = new StubUsuario(['id' => 7, 'nombre' => 'Master User']);
$controller = new CajaControllerTestDouble($cajaModel, $usuarioModel);

$resultado = $controller->procesar([
    'nombre' => 'Caja de prueba',
    'saldo_inicial' => 123.45,
]);

assertTrue($resultado['ok'] === true, 'La apertura debe ser exitosa cuando el usuario está en la base maestra.');
assertTrue($cajaModel->lastData['usuario_id'] === 7, 'La apertura debe usar el ID del usuario autenticado.');
assertTrue($cajaModel->lastData['nombre'] === 'Caja de prueba', 'Debe enviarse el nombre de la caja.');

// Caso 2: el usuario no existe ni en sesión ni en la base maestra.
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

fwrite(STDOUT, "CajaControllerTest: ok\n");
