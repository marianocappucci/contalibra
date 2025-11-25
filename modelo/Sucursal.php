<?php
require_once __DIR__ . '/../libs/DatabaseProvisioner.php';

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
        $empresaId = $data['empresa_id'] ?? null;
        if ($empresaId === null) {
            throw new RuntimeException('Debe indicar la empresa para crear la sucursal y su base.');
        }

        $this->db->beginTransaction();

        try {
            $stmt = $this->db->prepare("INSERT INTO sucursales (nombre, direccion, ciudad, empresa_id) VALUES (?,?,?,?)");
            $stmt->execute([
                $data['nombre'],
                $data['direccion'] ?? '',
                $data['ciudad'] ?? '',
                $empresaId
            ]);

            $sucursalId = (int) $this->db->lastInsertId();

            $empresaModel = new Empresa(Database::getDefaultStandaloneConnection());
            $empresa = $empresaModel->getByIdFromDefault((int) $empresaId);
            if (!$empresa) {
                throw new RuntimeException('No se encontró la empresa asociada para provisionar la base.');
            }

            $sucursalDbName = DatabaseProvisioner::generateSucursalDbName(
                $empresa['base_datos'] ?? '',
                $data['nombre'] ?? '',
                (int) $empresaId,
                $sucursalId
            );

            $pdoDb = DatabaseProvisioner::provisionDatabase($sucursalDbName);
            DatabaseProvisioner::restoreSchema($pdoDb);

            $tenantLabel = trim($empresa['nombre'] . ' - ' . ($data['nombre'] ?? 'Sucursal ' . $sucursalId));
            DatabaseProvisioner::registerCompanyDatabase($pdoDb, $tenantLabel, $sucursalDbName);

            if (isset($data['usuario_inicial'], $data['password_inicial'])
                && $data['usuario_inicial'] !== ''
                && $data['password_inicial'] !== '') {
                $roleId = DatabaseProvisioner::resolveRoleId($pdoDb, $data['rol_inicial'] ?? 'Superusuario');
                DatabaseProvisioner::createUser(
                    $pdoDb,
                    $data['usuario_inicial'],
                    $data['password_inicial'],
                    $roleId,
                    $sucursalDbName
                );
            }

            $this->db->commit();
            return true;
        } catch (Throwable $e) {
            if ($this->db->inTransaction()) {
                $this->db->rollBack();
            }

            throw new RuntimeException('No se pudo crear la sucursal: ' . $e->getMessage(), 0, $e);
        }
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
