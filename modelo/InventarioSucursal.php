<?php
class InventarioSucursal extends BaseModel
{
    public function getStock(int $sucursalId, int $productoId): float
    {
        $stmt = $this->db->prepare(
            "SELECT stock FROM inventarios_sucursal WHERE sucursal_id = ? AND producto_id = ? LIMIT 1"
        );
        $stmt->execute([$sucursalId, $productoId]);
        $result = $stmt->fetchColumn();

        return $result !== false ? (float) $result : 0.0;
    }

    public function resumenPorSucursal(?int $empresaId = null): array
    {
        $sql =
            "SELECT s.id AS sucursal_id, s.nombre AS sucursal_nombre, p.id AS producto_id, p.nombre AS producto_nombre, inv.stock " .
            "FROM inventarios_sucursal inv " .
            "INNER JOIN sucursales s ON s.id = inv.sucursal_id " .
            "INNER JOIN productos p ON p.id = inv.producto_id";

        $params = [];
        if ($empresaId !== null) {
            $sql .= " WHERE s.empresa_id = ?";
            $params[] = $empresaId;
        }

        $sql .= " ORDER BY s.nombre, p.nombre";

        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);

        return $stmt->fetchAll();
    }

    public function ajustarStock(int $sucursalId, int $productoId, float $cantidad): void
    {
        $this->runInTransaction(function () use ($sucursalId, $productoId, $cantidad) {
            $this->upsertDelta($sucursalId, $productoId, $cantidad);
            $this->assertStockNoNegative($sucursalId, $productoId);
        });
    }

    public function transferirStock(int $origenId, int $destinoId, int $productoId, float $cantidad, ?int $pedidoId = null): void
    {
        if ($cantidad <= 0) {
            throw new InvalidArgumentException('La cantidad a transferir debe ser mayor a cero.');
        }

        $this->runInTransaction(function () use ($origenId, $destinoId, $productoId, $cantidad, $pedidoId) {
            $this->upsertDelta($origenId, $productoId, -1 * $cantidad);
            $this->assertStockNoNegative($origenId, $productoId);

            $this->upsertDelta($destinoId, $productoId, $cantidad);

            $this->registrarTransferencia($origenId, $destinoId, $productoId, $cantidad, $pedidoId);
        });
    }

    public function registrarPedido(int $origenId, int $destinoId, array $items): int
    {
        if (empty($items)) {
            throw new InvalidArgumentException('Debe indicar al menos un producto para el pedido.');
        }

        return $this->runInTransaction(function () use ($origenId, $destinoId, $items) {
            $stmtPedido = $this->db->prepare(
                "INSERT INTO pedidos_sucursales (origen_id, destino_id, estado, creado_en) VALUES (?, ?, 'PENDIENTE', NOW())"
            );
            $stmtPedido->execute([$origenId, $destinoId]);
            $pedidoId = (int) $this->db->lastInsertId();

            $stmtDetalle = $this->db->prepare(
                "INSERT INTO pedidos_sucursales_detalle (pedido_id, producto_id, cantidad) VALUES (?, ?, ?)"
            );
            foreach ($items as $productoId => $cantidad) {
                $stmtDetalle->execute([$pedidoId, $productoId, $cantidad]);
            }

            return $pedidoId;
        });
    }

    public function atenderPedido(int $pedidoId): void
    {
        $pedido = $this->obtenerPedido($pedidoId);
        if ($pedido === null) {
            throw new RuntimeException('Pedido no encontrado.');
        }

        if ($pedido['estado'] !== 'PENDIENTE') {
            return;
        }

        $this->runInTransaction(function () use ($pedidoId, $pedido) {
            foreach ($pedido['items'] as $item) {
                $this->upsertDelta($pedido['origen_id'], (int) $item['producto_id'], -1 * (float) $item['cantidad']);
                $this->assertStockNoNegative($pedido['origen_id'], (int) $item['producto_id']);

                $this->upsertDelta($pedido['destino_id'], (int) $item['producto_id'], (float) $item['cantidad']);
                $this->registrarTransferencia($pedido['origen_id'], $pedido['destino_id'], (int) $item['producto_id'], (float) $item['cantidad'], $pedidoId);
            }

            $stmt = $this->db->prepare(
                "UPDATE pedidos_sucursales SET estado = 'ATENDIDO', atendido_en = NOW() WHERE id = ?"
            );
            $stmt->execute([$pedidoId]);
        });
    }

    public function listarPedidos(?string $estado = null): array
    {
        $sql =
            "SELECT pds.*, s_origen.nombre AS origen_nombre, s_destino.nombre AS destino_nombre " .
            "FROM pedidos_sucursales pds " .
            "INNER JOIN sucursales s_origen ON s_origen.id = pds.origen_id " .
            "INNER JOIN sucursales s_destino ON s_destino.id = pds.destino_id";
        $params = [];

        if ($estado !== null) {
            $sql .= " WHERE pds.estado = ?";
            $params[] = $estado;
        }

        $sql .= " ORDER BY pds.creado_en DESC";

        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);

        return $stmt->fetchAll();
    }

    public function obtenerPedido(int $pedidoId): ?array
    {
        $stmt = $this->db->prepare("SELECT * FROM pedidos_sucursales WHERE id = ? LIMIT 1");
        $stmt->execute([$pedidoId]);
        $pedido = $stmt->fetch();

        if (!$pedido) {
            return null;
        }

        $stmtDetalle = $this->db->prepare(
            "SELECT * FROM pedidos_sucursales_detalle WHERE pedido_id = ?"
        );
        $stmtDetalle->execute([$pedidoId]);
        $pedido['items'] = $stmtDetalle->fetchAll();

        return $pedido;
    }

    private function upsertDelta(int $sucursalId, int $productoId, float $cantidad): void
    {
        $stmt = $this->db->prepare(
            "INSERT INTO inventarios_sucursal (sucursal_id, producto_id, stock, actualizado_en) VALUES (?, ?, ?, NOW()) " .
            "ON DUPLICATE KEY UPDATE stock = stock + VALUES(stock), actualizado_en = VALUES(actualizado_en)"
        );
        $stmt->execute([$sucursalId, $productoId, $cantidad]);
    }

    private function registrarTransferencia(int $origenId, int $destinoId, int $productoId, float $cantidad, ?int $pedidoId = null): void
    {
        $stmt = $this->db->prepare(
            "INSERT INTO transferencias_inventario (origen_id, destino_id, producto_id, cantidad, pedido_id, registrado_en) VALUES (?, ?, ?, ?, ?, NOW())"
        );
        $stmt->execute([$origenId, $destinoId, $productoId, $cantidad, $pedidoId]);
    }

    private function assertStockNoNegative(int $sucursalId, int $productoId): void
    {
        $stockActual = $this->getStock($sucursalId, $productoId);
        if ($stockActual < 0) {
            throw new RuntimeException('Stock insuficiente en la sucursal.');
        }
    }

    private function runInTransaction(callable $callback)
    {
        $manageTransaction = !$this->db->inTransaction();
        if ($manageTransaction) {
            $this->db->beginTransaction();
        }

        try {
            $result = $callback();
            if ($manageTransaction) {
                $this->db->commit();
            }
            return $result;
        } catch (Exception $e) {
            if ($manageTransaction) {
                $this->db->rollBack();
            }
            throw $e;
        }
    }
}
