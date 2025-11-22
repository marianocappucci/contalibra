<?php
// Conexión simple usando PDO
class Database {
    private static $instance = null;
    private $pdo;
    private $dbName;

    private function __construct(?string $dbName = null) {
        $this->dbName = $dbName ?: $this->resolveDbName();

        $dsn = 'mysql:host=' . DB_HOST . ';dbname=' . $this->dbName . ';charset=utf8mb4';
        $options = [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ];
        try {
            $this->pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
        } catch (PDOException $e) {
            die('Error de conexión: ' . $e->getMessage());
        }
    }

    public static function getInstance(?string $dbName = null) {
        $activeDb = $dbName ?: self::currentDatabase();

        if (self::$instance === null || self::$instance->dbName !== $activeDb) {
            self::$instance = new Database($activeDb);
        }
        return self::$instance;
    }

    public static function setActiveDatabase(string $dbName): void
    {
        $_SESSION['db_name'] = $dbName;
        self::$instance = new Database($dbName);
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
}
