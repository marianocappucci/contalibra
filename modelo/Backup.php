<?php

class Backup
{
    private $con;

    public function __construct()
    {
        $this->con = new mysqli("localhost", "root", "", "contadb");
        $this->con->set_charset("utf8");
    }

    public function generarBackup()
    {
        $file = "backup_temp.sql";
        $tables = [];

        $result = $this->con->query("SHOW TABLES");
        while ($row = $result->fetch_row()) {
            $tables[] = $row[0];
        }

        $sql = "";

        foreach ($tables as $table) {
            // Estructura
            $res = $this->con->query("SHOW CREATE TABLE `$table`")->fetch_row();
            $sql .= "DROP TABLE IF EXISTS `$table`;\n";
            $sql .= $res[1] . ";\n\n";

            // Datos
            $res = $this->con->query("SELECT * FROM `$table`");
            while ($row = $res->fetch_assoc()) {
                $vals = array_map([$this->con, 'real_escape_string'], array_values($row));
                $vals = "'" . implode("','", $vals) . "'";
                $sql .= "INSERT INTO `$table` VALUES ($vals);\n";
            }

            $sql .= "\n";
        }

        file_put_contents($file, $sql);
        return $file;
    }


    public function restaurarBackup($path)
    {
        $sql = file_get_contents($path);
        if (!$sql) return false;

        $queries = explode(";\n", $sql);

        foreach ($queries as $q) {
            $q = trim($q);
            if ($q !== "") {
                @$this->con->query($q);
            }
        }

        return true;
    }
}
?>
