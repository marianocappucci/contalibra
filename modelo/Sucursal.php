<?php
class Sucursal extends BaseModel {
    public function getAll() {
        return $this->db->query("SELECT * FROM sucursales ORDER BY nombre")->fetchAll();
    }

    public function getById($id) {
        $stmt = $this->db->prepare("SELECT * FROM sucursales WHERE id = ?");
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    public function create($data) {
        $stmt = $this->db->prepare("INSERT INTO sucursales (nombre, direccion, ciudad) VALUES (?,?,?)");
        return $stmt->execute([
            $data['nombre'],
            $data['direccion'] ?? '',
            $data['ciudad'] ?? ''
        ]);
    }

    public function update($id, $data) {
        $stmt = $this->db->prepare("UPDATE sucursales SET nombre=?, direccion=?, ciudad=? WHERE id=?");
        return $stmt->execute([
            $data['nombre'],
            $data['direccion'] ?? '',
            $data['ciudad'] ?? '',
            $id
        ]);
    }

    public function delete($id) {
        $stmt = $this->db->prepare("DELETE FROM sucursales WHERE id=?");
        return $stmt->execute([$id]);
    }
}
