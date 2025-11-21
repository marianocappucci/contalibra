<?php
abstract class BaseModel {
    protected $db;

    public function __construct() {
        $this->db = Database::getInstance()->getConnection();
    }
}
