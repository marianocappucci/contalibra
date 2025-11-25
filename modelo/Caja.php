<?php
class Caja extends BaseModel {

    public function getAll() {
        return $this->db->query("SELECT c.*, u.nombre as usuario_apertura, pv.nombre AS punto_venta_nombre
                                 FROM cajas c
                                 LEFT JOIN usuarios u ON u.id = c.abierta_por
                                 LEFT JOIN puntos_venta pv ON pv.id = c.punto_venta_id
                                 ORDER BY c.id DESC")->fetchAll();
    }

    public function abrirCaja($data) {
        $stmt = $this->db->prepare("INSERT INTO cajas (nombre, saldo_inicial, abierta_por, fecha_apertura, estado, punto_venta_id) VALUES (?,?,?,?, 'ABIERTA', ?)");
        return $stmt->execute([
            $data['nombre'],
            $data['saldo_inicial'],
            $data['usuario_id'],
            date('Y-m-d H:i:s'),
            $data['punto_venta_id'] ?? null
        ]);
    }

    public function cerrarCaja($id, $usuarioId, $saldoFinal) {
        $stmt = $this->db->prepare("UPDATE cajas SET estado='CERRADA', saldo_final=?, cerrada_por=?, fecha_cierre=? WHERE id=?");
        return $stmt->execute([
            $saldoFinal,
            $usuarioId,
            date('Y-m-d H:i:s'),
            $id
        ]);
    }

    public function getCajaAbiertaPorUsuario($usuarioId) {
        $stmt = $this->db->prepare("SELECT * FROM cajas WHERE abierta_por = ? AND estado = 'ABIERTA' ORDER BY id DESC LIMIT 1");
        $stmt->execute([$usuarioId]);
        return $stmt->fetch();
    }
}
