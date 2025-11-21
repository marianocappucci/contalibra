<?php
require_once "libs/log_helper.php";
class LogController{public function index(){
    registrarLog("Acceso a index","Log");require_once 'modelo/Log.php';$c=new mysqli('localhost','root','','contadb');$logs=$c->query('SELECT * FROM logs ORDER BY fecha DESC');include 'vistas/logs/index.php';}}
?>