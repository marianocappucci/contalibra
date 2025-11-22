<?php
class Proveedor extends BaseModel {
    public function getAll() {
        return $this->db->query("SELECT * FROM proveedores ORDER BY nombre")->fetchAll();
    }

    public function getById($id) {
        $stmt = $this->db->prepare("SELECT * FROM proveedores WHERE id = ?");
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    public function create($data) {
        $stmt = $this->db->prepare("INSERT INTO proveedores (nombre, contacto, telefono, email) VALUES (?,?,?,?)");
        return $stmt->execute([
            $data['nombre'],
            $data['contacto'] ?? '',
            $data['telefono'] ?? '',
            $data['email'] ?? ''
        ]);
    }

    public function update($id, $data) {
        $stmt = $this->db->prepare("UPDATE proveedores SET nombre=?, contacto=?, telefono=?, email=? WHERE id=?");
        return $stmt->execute([
            $data['nombre'],
            $data['contacto'] ?? '',
            $data['telefono'] ?? '',
            $data['email'] ?? '',
            $id
        ]);
    }

    public function delete($id) {
        $stmt = $this->db->prepare("DELETE FROM proveedores WHERE id=?");
        return $stmt->execute([$id]);
    }
}
