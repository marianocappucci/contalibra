<?php
require_once "BaseModel.php";

class Log extends BaseModel
{
    public function registrar($usuario_id, $usuario_nombre, $accion, $modulo, $registro_id = null)
    {
        try {

            // Si el usuario no existe (login sin sesión), se deja NULL
            $uid = ($usuario_id > 0) ? $usuario_id : null;

            $sql = "INSERT INTO logs (usuario_id, usuario_nombre, accion, modulo, registro_id)
                    VALUES (:uid, :usuario_nombre, :accion, :modulo, :registro_id)";

            $stmt = $this->db->prepare($sql);

            return $stmt->execute([
                ':uid'            => $uid,
                ':usuario_nombre' => $usuario_nombre,
                ':accion'         => $accion,
                ':modulo'         => $modulo,
                ':registro_id'    => $registro_id
            ]);

        } catch (Exception $e) {
            error_log("Error en Log::registrar → " . $e->getMessage());
            return false;
        }
    }
}
