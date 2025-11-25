<?php
abstract class BaseModel {
    protected $db;

    public function __construct(?PDO $connection = null) {
        $this->db = $connection ?: Database::getInstance()->getConnection();
    }
}
