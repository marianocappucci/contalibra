<?php
// Conexión simple usando PDO
class Database {
    private static $instance = null;
    private $pdo;
    private $dbName;
    private $requestedDbName;
    private $fallbackUsed = false;

    private function __construct(?string $dbName = null) {
        $this->requestedDbName = $dbName ?: $this->resolveDbName();
        $this->connect($this->requestedDbName);
    }

    public static function getInstance(?string $dbName = null) {
        $activeDb = $dbName ?: self::currentDatabase();

        if (self::$instance === null || self::$instance->requestedDatabase() !== $activeDb) {
            self::$instance = new Database($activeDb);
            self::syncSessionAfterConnection($activeDb, self::$instance);
        }
        return self::$instance;
    }

    /**
     * Obtiene una conexión directa a la base de datos indicada sin modificar
     * la conexión activa ni las variables de sesión. Útil para consultar la
     * base maestra (contadb) aunque la app esté apuntando a una base de
     * datos de tenant.
     */
    public static function getStandaloneConnection(string $dbName): PDO
    {
        $isolated = new self($dbName);
        return $isolated->getConnection();
    }

    /**
     * Conexión directa a la base por defecto (contadb) sin cambiar la
     * conexión en uso por la app.
     */
    public static function getDefaultStandaloneConnection(): PDO
    {
        return self::getStandaloneConnection(DB_NAME);
    }

    public static function setActiveDatabase(string $dbName): void
    {
        $instance = new Database($dbName);
        self::$instance = $instance;
        self::syncSessionAfterConnection($dbName, $instance);
    }

    private static function currentDatabase(): string
    {
        return $_SESSION['db_name'] ?? DB_NAME;
    }

    private function resolveDbName(): string
    {
        return $_SESSION['db_name'] ?? DB_NAME;
    }

    public function getConnection() {
        return $this->pdo;
    }

    public function usedFallback(): bool
    {
        return $this->fallbackUsed === true;
    }

    public function requestedDatabase(): string
    {
        return $this->requestedDbName;
    }

    private function connect(string $dbName): void
    {
        $dsn = $this->buildDsn($dbName);

        try {
            $this->pdo = new PDO($dsn, DB_USER, DB_PASS, $this->pdoOptions());
            $this->dbName = $dbName;
        } catch (PDOException $e) {
            if ($this->isUnknownDatabaseError($e) && $dbName !== DB_NAME) {
                $this->fallbackUsed = true;
                $this->logUnknownDatabase($dbName, $e);
                $this->connectToDefault();
                return;
            }

            throw $e;
        }
    }

    private function connectToDefault(): void
    {
        $dsn = $this->buildDsn(DB_NAME);

        $this->pdo = new PDO($dsn, DB_USER, DB_PASS, $this->pdoOptions());
        $this->dbName = DB_NAME;
    }

    private function pdoOptions(): array
    {
        return [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ];
    }

    private function buildDsn(string $dbName): string
    {
        return 'mysql:host=' . DB_HOST . ';dbname=' . $dbName . ';charset=utf8mb4';
    }

    private function isUnknownDatabaseError(PDOException $e): bool
    {
        return $e->getCode() === '1049' || stripos($e->getMessage(), 'Unknown database') !== false;
    }

    private function logUnknownDatabase(string $dbName, PDOException $e): void
    {
        error_log(sprintf(
            '[%s] Base de datos no encontrada "%s": %s',
            date('c'),
            $dbName,
            $e->getMessage()
        ));
    }

    private static function syncSessionAfterConnection(string $requestedDb, self $instance): void
    {
        if ($instance->usedFallback()) {
            unset($_SESSION['db_name']);
            $_SESSION['db_fallback_message'] = sprintf(
                'La base de datos configurada (%s) no existe. Se usó la base por defecto.',
                $requestedDb
            );
            return;
        }

        $_SESSION['db_name'] = $instance->dbName;
        unset($_SESSION['db_fallback_message']);
    }
}
