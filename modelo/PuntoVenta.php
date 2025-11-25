<?php
class PuntoVenta extends BaseModel
{
    public function getAll(): array
    {
        return $this->db
            ->query("SELECT pv.*, s.nombre AS sucursal_nombre FROM puntos_venta pv LEFT JOIN sucursales s ON s.id = pv.sucursal_id ORDER BY pv.nombre")
            ->fetchAll();
    }

    public function getById(int $id)
    {
        $stmt = $this->db->prepare(
            "SELECT pv.*, s.nombre AS sucursal_nombre FROM puntos_venta pv LEFT JOIN sucursales s ON s.id = pv.sucursal_id WHERE pv.id = ?"
        );
        $stmt->execute([$id]);

        return $stmt->fetch();
    }

    public function getBySucursal(int $sucursalId): array
    {
        $stmt = $this->db->prepare(
            "SELECT * FROM puntos_venta WHERE sucursal_id = ? ORDER BY nombre"
        );
        $stmt->execute([$sucursalId]);

        return $stmt->fetchAll();
    }

    public function create(array $data): int
    {
        $stmt = $this->db->prepare(
            "INSERT INTO puntos_venta (sucursal_id, nombre, codigo, activo, creado_en) VALUES (?,?,?,?,NOW())"
        );
        $stmt->execute([
            $data['sucursal_id'],
            $data['nombre'],
            $data['codigo'] ?? null,
            $data['activo'] ?? 1,
        ]);

        return (int) $this->db->lastInsertId();
    }

    public function update(int $id, array $data): bool
    {
        $stmt = $this->db->prepare(
            "UPDATE puntos_venta SET nombre = ?, codigo = ?, activo = ?, sucursal_id = ? WHERE id = ?"
        );

        return $stmt->execute([
            $data['nombre'],
            $data['codigo'] ?? null,
            $data['activo'] ?? 1,
            $data['sucursal_id'],
            $id,
        ]);
    }

    public function delete(int $id): bool
    {
        $stmt = $this->db->prepare("DELETE FROM puntos_venta WHERE id = ?");
        return $stmt->execute([$id]);
    }
}
