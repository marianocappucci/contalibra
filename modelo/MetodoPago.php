<?php
class MetodoPago extends BaseModel {
    public function getAll() {
        return $this->db->query("SELECT * FROM metodos_pago ORDER BY nombre")->fetchAll();
    }

    public function getById($id) {
        $stmt = $this->db->prepare("SELECT * FROM metodos_pago WHERE id = ?");
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    public function create($data) {
        $stmt = $this->db->prepare("INSERT INTO metodos_pago (nombre, descripcion) VALUES (?,?)");
        return $stmt->execute([
            $data['nombre'],
            $data['descripcion'] ?? ''
        ]);
    }

    public function update($id, $data) {
        $stmt = $this->db->prepare("UPDATE metodos_pago SET nombre=?, descripcion=? WHERE id=?");
        return $stmt->execute([
            $data['nombre'],
            $data['descripcion'] ?? '',
            $id
        ]);
    }

    public function delete($id) {
        $stmt = $this->db->prepare("DELETE FROM metodos_pago WHERE id=?");
        return $stmt->execute([$id]);
    }
}
