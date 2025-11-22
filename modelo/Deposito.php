<?php
class Deposito extends BaseModel {
    public function getAll() {
        $sql = "SELECT d.*, s.nombre as sucursal_nombre FROM depositos d LEFT JOIN sucursales s ON s.id = d.sucursal_id ORDER BY d.nombre";
        return $this->db->query($sql)->fetchAll();
    }

    public function getById($id) {
        $stmt = $this->db->prepare("SELECT * FROM depositos WHERE id = ?");
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    public function create($data) {
        $stmt = $this->db->prepare("INSERT INTO depositos (nombre, descripcion, sucursal_id) VALUES (?,?,?)");
        return $stmt->execute([
            $data['nombre'],
            $data['descripcion'] ?? '',
            $data['sucursal_id'] ?? null
        ]);
    }

    public function update($id, $data) {
        $stmt = $this->db->prepare("UPDATE depositos SET nombre=?, descripcion=?, sucursal_id=? WHERE id=?");
        return $stmt->execute([
            $data['nombre'],
            $data['descripcion'] ?? '',
            $data['sucursal_id'] ?? null,
            $id
        ]);
    }

    public function delete($id) {
        $stmt = $this->db->prepare("DELETE FROM depositos WHERE id=?");
        return $stmt->execute([$id]);
    }
}
