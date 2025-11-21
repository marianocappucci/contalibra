<?php

class BackupController
{
    public function index()
    {
        include 'vistas/config/backup.php';
    }

    public function generar()
    {
        include 'modelo/Backup.php';
        $backup = new Backup();
        $file = $backup->generarBackup();

        header("Content-Disposition: attachment; filename=\"contadb_backup_" . date('Ymd_His') . ".sql\"");
        header("Content-Type: application/sql");
        readfile($file);
        exit;
    }

    public function restaurar()
    {
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
