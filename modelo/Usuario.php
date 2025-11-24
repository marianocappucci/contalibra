<?php
class Usuario extends BaseModel {

public function getByUsername($username) {
    $stmt = $this->db->prepare("SELECT u.*, r.nombre as rol_nombre
                                FROM usuarios u
                                LEFT JOIN roles r ON r.id = u.rol_id
                                WHERE u.username = ? AND u.activo = 1
                                LIMIT 1");
    $stmt->execute([$username]);
    return $stmt->fetch();
}


    public function getAll() {
        $sql = "SELECT u.*, r.rol_nombre as rol_nombre
                FROM usuarios u
                LEFT JOIN roles r ON r.id = u.rol_id";
        return $this->db->query($sql)->fetchAll();
    }

    public function create(array $data) {
        $stmt = $this->db->prepare("INSERT INTO usuarios(nombre, usuario, password, rol_id, estado)
                                    VALUES(?,?,?,?,?)");
        return $stmt->execute([
            $data['nombre'],
            $data['usuario'],
            $data['password'],
            $data['rol_id'],
            $data['estado']
        ]);
    }

    public function updatePassword(int $id, string $hashedPassword): bool
    {
        $stmt = $this->db->prepare("UPDATE usuarios SET password=? WHERE id=?");
        return $stmt->execute([$hashedPassword, $id]);
    }

    public function delete($id) {
        $stmt = $this->db->prepare("DELETE FROM usuarios WHERE id=?");
        return $stmt->execute([$id]);
    }
}
