<?php
function registrarLog($accion,$modulo,$registro_id=null){
    require_once "modelo/Log.php";
    if(session_status()===PHP_SESSION_NONE) session_start();
    $u=$_SESSION['user']['id'] ?? null;
    $n=$_SESSION['user']['nombre'] ?? "Desconocido";
    $log=new Log();
    $log->registrar($u,$n,$accion,$modulo,$registro_id);
}
?>