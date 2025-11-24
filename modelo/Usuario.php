<?php
class Usuario extends BaseModel {

    public function getByUsername($username) {
        $sql = "SELECT
                    u.id,
                    u.nombre,
                    u.username,
                    u.password,
                    u.rol_id,
                    u.activo,
                    u.base_datos,
                    roles.nombre AS rol_nombre
                FROM usuarios u
                LEFT JOIN roles ON roles.id = u.rol_id
                WHERE u.username = ? AND u.activo = 1
                LIMIT 1";

        $stmt = $this->db->prepare($sql);
        $stmt->execute([$username]);
        return $stmt->fetch();
    }

    public function getById($id)
    {
        $sql = "SELECT
                    u.id,
                    u.nombre,
                    u.username,
                    u.password,
                    u.rol_id,
                    u.activo,
                    u.base_datos,
                    roles.nombre AS rol_nombre
                FROM usuarios u
                LEFT JOIN roles ON roles.id = u.rol_id
                WHERE u.id = ? AND u.activo = 1
                LIMIT 1";

        $stmt = $this->db->prepare($sql);
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    public function getAll() {
        $sql = "SELECT
                    u.id,
                    u.nombre,
                    u.username,
                    u.password,
                    u.rol_id,
                    u.activo,
                    u.base_datos,
                    roles.nombre AS rol_nombre
                FROM usuarios u
                LEFT JOIN roles ON roles.id = u.rol_id";
        return $this->db->query($sql)->fetchAll();
    }

    public function create(array $data) {
       $stmt = $this->db->prepare("INSERT INTO usuarios(nombre, username, password, rol_id, activo, base_datos)
                                    VALUES(?,?,?,?,?,?)");
        return $stmt->execute([
            $data['nombre'],
            $data['username'],
            $data['password'],
            $data['rol_id'],
            $data['activo'],
            $data['base_datos']
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
