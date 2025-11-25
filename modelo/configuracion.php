<?php
class Configuracion extends BaseModel {

    public function get() {
        return $this->db->query("SELECT * FROM configuracion LIMIT 1")->fetch();
    }

    public function setNombreFantasia(string $nombre): bool
    {
        $stmt = $this->db->prepare('UPDATE configuracion SET nombre_fantasia = ?, actualizado = NOW() WHERE id = 1');
        return $stmt->execute([$nombre]);
    }

    public function update($data) {
        $stmt = $this->db->prepare("UPDATE configuracion
            SET nombre_fantasia=?, direccion=?, telefono=?, cuit=?, punto_venta=?, actualizado=NOW()
            WHERE id = 1");
        return $stmt->execute([
            $data['nombre_fantasia'],
            $data['direccion'],
            $data['telefono'],
            $data['cuit'],
            $data['punto_venta']
        ]);
    }
}
