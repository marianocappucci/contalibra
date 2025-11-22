<?php
class Cliente extends BaseModel {
    public function getAll() {
        return $this->db->query("SELECT * FROM clientes ORDER BY nombre")->fetchAll();
    }

    public function getById($id) {
        $stmt = $this->db->prepare("SELECT * FROM clientes WHERE id = ?");
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    public function create($data) {
        $stmt = $this->db->prepare("INSERT INTO clientes (nombre, tipo, documento, email, direccion, saldo) VALUES (?,?,?,?,?,?)");
        $stmt->execute([
            $data['nombre'],
            $data['tipo'] ?? 'Consumidor Final',
            $data['documento'] ?? '',
            $data['email'] ?? '',
            $data['direccion'] ?? '',
            $data['saldo'] ?? 0
        ]);
        return $this->db->lastInsertId();
    }

    public function update($id, $data) {
        $stmt = $this->db->prepare("UPDATE clientes SET nombre=?, tipo=?, documento=?, email=?, direccion=?, saldo=? WHERE id=?");
        return $stmt->execute([
            $data['nombre'],
            $data['tipo'] ?? 'Consumidor Final',
            $data['documento'] ?? '',
            $data['email'] ?? '',
            $data['direccion'] ?? '',
            $data['saldo'] ?? 0,
            $id
        ]);
    }

    public function delete($id) {
        $stmt = $this->db->prepare("DELETE FROM clientes WHERE id=?");
        return $stmt->execute([$id]);
    }
}
