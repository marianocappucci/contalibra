<?php
class Empresa extends BaseModel
{
    public function getAll(): array
    {
        return $this->db
            ->query("SELECT * FROM empresas ORDER BY nombre")
            ->fetchAll();
    }

    public function getById(int $id)
    {
        $stmt = $this->db->prepare("SELECT * FROM empresas WHERE id = ? LIMIT 1");
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    public function create(array $data): int
    {
        $stmt = $this->db->prepare(
            "INSERT INTO empresas (nombre, base_datos, creado_en) VALUES (?,?,NOW())"
        );
        $stmt->execute([
            $data['nombre'],
            $data['base_datos'] ?? null,
        ]);

        return (int) $this->db->lastInsertId();
    }

    public function update(int $id, array $data): bool
    {
        $stmt = $this->db->prepare(
            "UPDATE empresas SET nombre = ?, base_datos = ? WHERE id = ?"
        );

        return $stmt->execute([
            $data['nombre'],
            $data['base_datos'] ?? null,
            $id,
        ]);
    }

    public function delete(int $id): bool
    {
        $stmt = $this->db->prepare("DELETE FROM empresas WHERE id = ?");
        return $stmt->execute([$id]);
    }

    public function sucursalesConPuntosVenta(int $empresaId): array
    {
        $stmt = $this->db->prepare(
            "SELECT s.*, pv.id AS punto_venta_id, pv.nombre AS punto_venta_nombre, pv.codigo AS punto_venta_codigo, pv.activo AS punto_venta_activo " .
            "FROM sucursales s " .
            "LEFT JOIN puntos_venta pv ON pv.sucursal_id = s.id " .
            "WHERE s.empresa_id = ? " .
            "ORDER BY s.nombre, pv.nombre"
        );
        $stmt->execute([$empresaId]);
        $rows = $stmt->fetchAll();

        $resultado = [];
        foreach ($rows as $row) {
            $sucursalId = (int) $row['id'];
            if (!isset($resultado[$sucursalId])) {
                $resultado[$sucursalId] = [
                    'id' => $sucursalId,
                    'nombre' => $row['nombre'],
                    'direccion' => $row['direccion'],
                    'ciudad' => $row['ciudad'],
                    'empresa_id' => $row['empresa_id'],
                    'puntos_venta' => [],
                ];
            }

            if ($row['punto_venta_id'] !== null) {
                $resultado[$sucursalId]['puntos_venta'][] = [
                    'id' => (int) $row['punto_venta_id'],
                    'nombre' => $row['punto_venta_nombre'],
                    'codigo' => $row['punto_venta_codigo'],
                    'activo' => (bool) $row['punto_venta_activo'],
                ];
            }
        }

        return array_values($resultado);
    }

    public function inventarioTotal(int $empresaId): array
    {
        $stmt = $this->db->prepare(
            "SELECT p.id AS producto_id, p.nombre AS producto_nombre, SUM(inv.stock) AS stock_total " .
            "FROM inventarios_sucursal inv " .
            "INNER JOIN productos p ON p.id = inv.producto_id " .
            "INNER JOIN sucursales s ON s.id = inv.sucursal_id " .
            "WHERE s.empresa_id = ? " .
            "GROUP BY p.id, p.nombre " .
            "ORDER BY p.nombre"
        );
        $stmt->execute([$empresaId]);

        return $stmt->fetchAll();
    }
}
