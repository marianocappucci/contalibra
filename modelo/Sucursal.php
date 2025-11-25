<?php
class Sucursal extends BaseModel {
    public function getAll() {
        $hasEmpresasTable = $this->tableExists('empresas');

        $sql = $hasEmpresasTable
            ? "SELECT s.*, e.nombre AS empresa_nombre FROM sucursales s LEFT JOIN empresas e ON e.id = s.empresa_id ORDER BY s.nombre"
            : "SELECT s.*, NULL AS empresa_nombre FROM sucursales s ORDER BY s.nombre";

        return $this->db->query($sql)->fetchAll();
    }

    public function getById($id) {
        $stmt = $this->db->prepare("SELECT * FROM sucursales WHERE id = ?");
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    public function create($data) {
        $stmt = $this->db->prepare("INSERT INTO sucursales (nombre, direccion, ciudad, empresa_id) VALUES (?,?,?,?)");
        return $stmt->execute([
            $data['nombre'],
            $data['direccion'] ?? '',
            $data['ciudad'] ?? '',
            $data['empresa_id'] ?? null
        ]);
    }

    public function update($id, $data) {
        $stmt = $this->db->prepare("UPDATE sucursales SET nombre=?, direccion=?, ciudad=?, empresa_id=? WHERE id=?");
        return $stmt->execute([
            $data['nombre'],
            $data['direccion'] ?? '',
            $data['ciudad'] ?? '',
            $data['empresa_id'] ?? null,
            $id
        ]);
    }

    public function getByEmpresa($empresaId) {
        $stmt = $this->db->prepare("SELECT * FROM sucursales WHERE empresa_id = ? ORDER BY nombre");
        $stmt->execute([$empresaId]);
        return $stmt->fetchAll();
    }

    public function delete($id) {
        $stmt = $this->db->prepare("DELETE FROM sucursales WHERE id=?");
        return $stmt->execute([$id]);
    }

    private function tableExists(string $table): bool
    {
        $stmt = $this->db->prepare('SHOW TABLES LIKE ?');
        $stmt->execute([$table]);

        return (bool) $stmt->fetchColumn();
    }
}
