<?php
class Usuario extends BaseModel {

    public function getByUsername($username) {
        $stmt = $this->db->prepare("SELECT u.*, r.nombre as rol_nombre 
                                    FROM usuarios u
                                    LEFT JOIN roles r ON r.id = u.rol_id
                                    WHERE username = ? AND activo = 1 LIMIT 1");
        $stmt->execute([$username]);
        return $stmt->fetch();
    }

    public function getAll() {
        $sql = "SELECT u.*, r.nombre as rol_nombre 
                FROM usuarios u
                LEFT JOIN roles r ON r.id = u.rol_id
                ORDER BY u.id DESC";
        return $this->db->query($sql)->fetchAll();
    }

    public function getRoles() {
        return $this->db->query("SELECT * FROM roles ORDER BY nombre")->fetchAll();
    }

    public function getById($id) {
        $stmt = $this->db->prepare("SELECT * FROM usuarios WHERE id = ?");
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    public function create($data) {
        $stmt = $this->db->prepare("INSERT INTO usuarios (nombre, username, password, rol_id, activo) VALUES (?,?,?,?,?)");
        return $stmt->execute([
            $data['nombre'],
            $data['username'],
            $data['password'], // demo: se guarda plano, mejorar con password_hash
            $data['rol_id'],
            isset($data['activo']) ? 1 : 0
        ]);
    }

    public function update($id, $data) {
        $stmt = $this->db->prepare("UPDATE usuarios SET nombre=?, username=?, rol_id=?, activo=? WHERE id=?");
        return $stmt->execute([
            $data['nombre'],
            $data['username'],
            $data['rol_id'],
            isset($data['activo']) ? 1 : 0,
            $id
        ]);
    }

    public function delete($id) {
        $stmt = $this->db->prepare("DELETE FROM usuarios WHERE id=?");
        return $stmt->execute([$id]);
    }
}
