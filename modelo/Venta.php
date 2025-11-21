<?php
class Venta extends BaseModel {

    public function crearVenta($data, $items) {
        try {
            $this->db->beginTransaction();

            $stmt = $this->db->prepare("INSERT INTO ventas (caja_id, usuario_id, cliente, subtotal, iva, total, fecha, estado, tipo_comprobante) 
                                        VALUES (?,?,?,?,?,?,?,?,?)");
            $stmt->execute([
                $data['caja_id'],
                $data['usuario_id'],
                $data['cliente'],
                $data['subtotal'],
                $data['iva'],
                $data['total'],
                date('Y-m-d H:i:s'),
                'PENDIENTE',
                $data['tipo_comprobante']
            ]);
            $ventaId = $this->db->lastInsertId();

            $stmtItem = $this->db->prepare("INSERT INTO ventas_detalle (venta_id, producto_id, cantidad, precio_unitario, total) 
                                            VALUES (?,?,?,?,?)");
            $stmtStock = $this->db->prepare("UPDATE productos SET stock = stock - ? WHERE id = ?");

            foreach ($items as $it) {
                $stmtItem->execute([
                    $ventaId,
                    $it['producto_id'],
                    $it['cantidad'],
                    $it['precio_unitario'],
                    $it['total']
                ]);
                $stmtStock->execute([$it['cantidad'], $it['producto_id']]);
            }

            $this->db->commit();
            return $ventaId;
        } catch (Exception $e) {
            $this->db->rollBack();
            throw $e;
        }
    }

    public function getById($id) {
        $stmt = $this->db->prepare("SELECT * FROM ventas WHERE id = ?");
        $stmt->execute([$id]);
        $venta = $stmt->fetch();

        if ($venta) {
            $stmtDet = $this->db->prepare("SELECT vd.*, p.nombre as producto_nombre 
                                           FROM ventas_detalle vd
                                           LEFT JOIN productos p ON p.id = vd.producto_id
                                           WHERE vd.venta_id = ?");
            $stmtDet->execute([$id]);
            $venta['items'] = $stmtDet->fetchAll();
        }
        return $venta;
    }

    public function listarVentas($desde = null, $hasta = null) {
        $sql = "SELECT v.*, u.nombre as usuario_nombre 
                FROM ventas v
                LEFT JOIN usuarios u ON u.id = v.usuario_id
                WHERE 1=1";
        $params = [];
        if ($desde) {
            $sql .= " AND DATE(v.fecha) >= ?";
            $params[] = $desde;
        }
        if ($hasta) {
            $sql .= " AND DATE(v.fecha) <= ?";
            $params[] = $hasta;
        }
        $sql .= " ORDER BY v.fecha DESC";
        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll();
    }
}
