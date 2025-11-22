<?php
class Producto extends BaseModel {

    public function getAll() {
        $sql = "SELECT p.*, lp.nombre as lista_nombre, pr.nombre as proveedor_nombre, d.nombre as deposito_nombre
                FROM productos p
                LEFT JOIN listas_precios lp ON lp.id = p.lista_precio_id
                LEFT JOIN proveedores pr ON pr.id = p.proveedor_id
                LEFT JOIN depositos d ON d.id = p.deposito_id
                ORDER BY p.id DESC";
        return $this->db->query($sql)->fetchAll();
    }

    public function getById($id) {
        $stmt = $this->db->prepare("SELECT * FROM productos WHERE id = ?");
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

public function buscarPorNombre($term) {
    $stmt = $this->db->prepare("
        SELECT id, nombre, precio, stock 
        FROM productos 
        WHERE nombre LIKE ? AND activo = 1 
        ORDER BY nombre LIMIT 15
    ");
    $stmt->execute(["%$term%"]);
    return $stmt->fetchAll();
}


    public function create($data) {
        $stmt = $this->db->prepare("INSERT INTO productos (nombre, sku, codigo_barras, precio, lista_precio_id, stock, proveedor_id, deposito_id, activo) VALUES (?,?,?,?,?,?,?,?,?)");
        return $stmt->execute([
            $data['nombre'],
            $data['sku'],
            $data['codigo_barras'] ?? '',
            $data['precio'],
            $data['lista_precio_id'],
            $data['stock'],
            $data['proveedor_id'] ?? null,
            $data['deposito_id'] ?? null,
            isset($data['activo']) ? 1 : 0
        ]);
    }

    public function update($id, $data) {
        $stmt = $this->db->prepare("UPDATE productos SET nombre=?, sku=?, codigo_barras=?, precio=?, lista_precio_id=?, stock=?, proveedor_id=?, deposito_id=?, activo=? WHERE id=?");
        return $stmt->execute([
            $data['nombre'],
            $data['sku'],
            $data['codigo_barras'] ?? '',
            $data['precio'],
            $data['lista_precio_id'],
            $data['stock'],
            $data['proveedor_id'] ?? null,
            $data['deposito_id'] ?? null,
            isset($data['activo']) ? 1 : 0,
            $id
        ]);
    }

    public function delete($id) {
        $stmt = $this->db->prepare("DELETE FROM productos WHERE id=?");
        return $stmt->execute([$id]);
    }

    public function actualizarStock($id, $cantidadDelta) {
        $stmt = $this->db->prepare("UPDATE productos SET stock = stock + ? WHERE id = ?");
        return $stmt->execute([$cantidadDelta, $id]);
    }
}
