<?php
require_once "libs/log_helper.php";

class BackupController
{
    public function index(){
    registrarLog("Acceso a index","Backup");
        include 'vistas/config/backup.php';
    }

    public function generar(){
    registrarLog("Acceso a generar","Backup");
        include 'modelo/Backup.php';
        $backup = new Backup();
        $file = $backup->generarBackup();

        header("Content-Disposition: attachment; filename=\"contadb_backup_" . date('Ymd_His') . ".sql\"");
        header("Content-Type: application/sql");
        readfile($file);
        exit;
    }

    public function restaurar(){
    registrarLog("Acceso a restaurar","Backup");
        if (!isset($_FILES['archivo'])) {
            $msg = "No se seleccionó ningún archivo.";
            include 'vistas/config/backup.php';
            return;
        }

        include 'modelo/Backup.php';
        $backup = new Backup();

        $sqlFile = $_FILES['archivo']['tmp_name'];
        $resultado = $backup->restaurarBackup($sqlFile);

        $msg = $resultado ? 
            "La base de datos fue restaurada correctamente." : 
            "Ocurrió un error al restaurar la base de datos.";

        include 'vistas/config/backup.php';
    }
}
?>
