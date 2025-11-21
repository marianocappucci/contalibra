<?php
class ListaPrecio extends BaseModel {

    public function getAll() {
        return $this->db->query("SELECT * FROM listas_precios ORDER BY nombre")->fetchAll();
    }
}
