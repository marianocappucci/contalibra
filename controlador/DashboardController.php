<?php
require_once "libs/log_helper.php";
class DashboardController {
    public function index(){
    registrarLog("Acceso a index","Dashboard");
        include __DIR__ . '/../vistas/dashboard/index.php';
    }
}
