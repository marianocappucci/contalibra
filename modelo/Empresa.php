<?php
require_once __DIR__ . '/../libs/DatabaseProvisioner.php';

class Empresa extends BaseModel
{
    public function getAll(): array
    {
        $connection = $this->empresasConnection();
        if ($connection === null) {
            return [];
        }

        $empresas = $connection
            ->query("SELECT * FROM empresas ORDER BY nombre")
            ->fetchAll();

        $resultados = [];
        foreach ($empresas as $empresa) {
            if (!$this->databaseExists($connection, $empresa['base_datos'])) {
                $this->delete((int) $empresa['id']);
                continue;
            }

            $resultados[] = $empresa;
        }

        return $resultados;
    }

    public function getById(int $id)
    {
        $connection = $this->empresasConnection();
        if ($connection === null) {
            return null;
        }

        $stmt = $connection->prepare("SELECT * FROM empresas WHERE id = ? LIMIT 1");
        $stmt->execute([$id]);

        return $stmt->fetch();
    }

    /**
     * Obtiene una empresa usando siempre la base maestra, sin depender de la
     * base de datos activa en el contexto del inquilino.
     */
    public function getByIdFromDefault(int $id)
    {
        $connection = $this->empresasConnection();
        if ($connection === null) {
            return null;
        }

        $stmt = $connection->prepare("SELECT * FROM empresas WHERE id = ? LIMIT 1");
        $stmt->execute([$id]);

        return $stmt->fetch();
    }

    public function getByBaseDatos(string $dbName)
    {
        $connection = $this->empresasConnection();
        if ($connection === null) {
            return null;
        }

        $stmt = $connection->prepare("SELECT * FROM empresas WHERE base_datos = ? LIMIT 1");
        $stmt->execute([$dbName]);

        $empresa = $stmt->fetch();

        if ($empresa && !$this->databaseExists($connection, $empresa['base_datos'])) {
            $this->delete((int) $empresa['id']);
            return null;
        }

        return $empresa;
    }

    public function create(array $data): int
    {
        $connection = $this->empresasConnection();
        if ($connection === null) {
            throw new RuntimeException('No se pudo conectar a la base maestra de empresas.');
        }

        $nombre = trim($data['nombre'] ?? '');
        if ($nombre === '') {
            throw new RuntimeException('El nombre de la empresa es obligatorio.');
        }

        $dbName = isset($data['base_datos']) && $data['base_datos'] !== ''
            ? DatabaseProvisioner::sanitizeDbName($data['base_datos'])
            : DatabaseProvisioner::generateCompanyDbName($nombre);

        try {
            $pdoDb = DatabaseProvisioner::provisionDatabase($dbName);
            DatabaseProvisioner::restoreSchema($pdoDb);
            DatabaseProvisioner::registerCompanyDatabase($pdoDb, $nombre, $dbName);

            if (isset($data['master_user'], $data['master_pass'])
                && $data['master_user'] !== ''
                && $data['master_pass'] !== '') {
                $roleId = DatabaseProvisioner::resolveRoleId($pdoDb, $data['master_role'] ?? 'Superusuario');
                DatabaseProvisioner::createUser($pdoDb, $data['master_user'], $data['master_pass'], $roleId, $dbName);
            }
        } catch (Throwable $e) {
            throw new RuntimeException('No se pudo provisionar la base de la empresa: ' . $e->getMessage(), 0, $e);
        }

        $stmt = $connection->prepare(
            "INSERT INTO empresas (nombre, base_datos, creado_en) VALUES (?,?,NOW())"
        );
        $stmt->execute([
            $nombre,
            $dbName,
        ]);

        $empresaId = (int) $connection->lastInsertId();

        $this->configurarDatosIniciales($pdoDb, $empresaId, $nombre, $dbName);

        return $empresaId;
    }

    public function update(int $id, array $data): bool
    {
        $connection = $this->empresasConnection();
        if ($connection === null) {
            return false;
        }

        $stmt = $connection->prepare(
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
        $connection = $this->empresasConnection();
        if ($connection === null) {
            return false;
        }

        $stmt = $connection->prepare("DELETE FROM empresas WHERE id = ?");

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

    private function empresasConnection(): ?PDO
    {
        $connection = Database::getDefaultStandaloneConnection();

        return $this->tableExists($connection, 'empresas') ? $connection : null;
    }

    private function tableExists(PDO $connection, string $table): bool
    {
        $stmt = $connection->prepare('SHOW TABLES LIKE ?');
        $stmt->execute([$table]);

        return (bool) $stmt->fetchColumn();
    }

    private function databaseExists(PDO $connection, string $dbName): bool
    {
        $stmt = $connection->prepare('SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = ?');
        $stmt->execute([$dbName]);

        return (bool) $stmt->fetchColumn();
    }

    private function configurarDatosIniciales(PDO $pdoDb, int $empresaId, string $nombre, string $dbName): void
    {
        $pdoDb->beginTransaction();

        try {
            $pdoDb->exec('SET FOREIGN_KEY_CHECKS=0');

            $this->sincronizarEmpresaBase($pdoDb, $empresaId, $nombre, $dbName);
            $sucursalId = $this->asegurarSucursalPrincipal($pdoDb, $empresaId);
            $this->asegurarPuntoVentaPrincipal($pdoDb, $sucursalId);
            $this->crearSuperusuarioInicial($pdoDb, $empresaId, $dbName);
            $this->actualizarNombreFantasia($pdoDb, $nombre);

            $pdoDb->exec('SET FOREIGN_KEY_CHECKS=1');
            $pdoDb->commit();
        } catch (Throwable $e) {
            if ($pdoDb->inTransaction()) {
                $pdoDb->rollBack();
            }

            $pdoDb->exec('SET FOREIGN_KEY_CHECKS=1');

            throw new RuntimeException(
                'No se pudieron configurar los datos iniciales de la empresa recién creada: ' . $e->getMessage(),
                0,
                $e
            );
        }
    }

    private function sincronizarEmpresaBase(PDO $pdoDb, int $empresaId, string $nombre, string $dbName): void
    {
        $empresa = $pdoDb->query('SELECT id FROM empresas ORDER BY id ASC LIMIT 1')->fetch();

        if ($empresa) {
            $update = $pdoDb->prepare('UPDATE empresas SET id = ?, nombre = ?, base_datos = ? WHERE id = ?');
            $update->execute([$empresaId, $nombre, $dbName, $empresa['id']]);
        } else {
            $insert = $pdoDb->prepare('INSERT INTO empresas (id, nombre, base_datos, creado_en) VALUES (?,?,?,NOW())');
            $insert->execute([$empresaId, $nombre, $dbName]);
        }

        $pdoDb->exec('ALTER TABLE empresas AUTO_INCREMENT = ' . ($empresaId + 1));
    }

    private function asegurarSucursalPrincipal(PDO $pdoDb, int $empresaId): int
    {
        $sucursal = $pdoDb->query('SELECT * FROM sucursales ORDER BY id ASC LIMIT 1')->fetch();
        $oldSucursalId = $sucursal ? (int) $sucursal['id'] : null;

        if ($sucursal) {
            $stmt = $pdoDb->prepare('UPDATE sucursales SET empresa_id = ?, nombre = COALESCE(NULLIF(nombre, ""), "Sucursal principal") WHERE id = ?');
            $stmt->execute([$empresaId, $sucursal['id']]);
            $sucursalId = (int) $sucursal['id'];
        } else {
            $stmt = $pdoDb->prepare('INSERT INTO sucursales (nombre, direccion, ciudad, empresa_id) VALUES (?,?,?,?)');
            $stmt->execute(['Sucursal principal', '', '', $empresaId]);
            $sucursalId = (int) $pdoDb->lastInsertId();
        }

        $depositoUpdate = $pdoDb->prepare('UPDATE depositos SET sucursal_id = ? WHERE sucursal_id IS NULL OR sucursal_id = ?');
        $depositoUpdate->execute([$sucursalId, $oldSucursalId ?? $sucursalId]);

        $pdoDb->exec('ALTER TABLE sucursales AUTO_INCREMENT = ' . ($sucursalId + 1));

        return $sucursalId;
    }

    private function asegurarPuntoVentaPrincipal(PDO $pdoDb, int $sucursalId): void
    {
        $puntoVenta = $pdoDb
            ->prepare('SELECT id FROM puntos_venta WHERE sucursal_id = ? ORDER BY id ASC LIMIT 1');
        $puntoVenta->execute([$sucursalId]);
        $pv = $puntoVenta->fetch();

        if ($pv) {
            $update = $pdoDb->prepare('UPDATE puntos_venta SET sucursal_id = ?, nombre = COALESCE(NULLIF(nombre, ""), "Punto de venta principal"), codigo = COALESCE(NULLIF(codigo, ""), "0001"), activo = 1 WHERE id = ?');
            $update->execute([$sucursalId, $pv['id']]);
            $pvId = (int) $pv['id'];
        } else {
            $insert = $pdoDb->prepare(
                'INSERT INTO puntos_venta (sucursal_id, nombre, codigo, activo, creado_en) VALUES (?,?,?,?,NOW())'
            );
            $insert->execute([$sucursalId, 'Punto de venta principal', '0001', 1]);
            $pvId = (int) $pdoDb->lastInsertId();
        }

        $pdoDb->exec('ALTER TABLE puntos_venta AUTO_INCREMENT = ' . ($pvId + 1));
    }

    private function actualizarNombreFantasia(PDO $pdoDb, string $nombre): void
    {
        $stmt = $pdoDb->prepare('UPDATE configuracion SET nombre_fantasia = ?, actualizado = NOW() WHERE id = 1');
        $stmt->execute([$nombre]);
    }

    private function crearSuperusuarioInicial(PDO $pdoDb, int $empresaId, string $dbName): void
    {
        $usuarioExistente = $pdoDb->prepare('SELECT id FROM usuarios WHERE username = ? AND base_datos = ? LIMIT 1');
        $usuarioExistente->execute(['root', $dbName]);

        if ($usuarioExistente->fetchColumn()) {
            return;
        }

        $rolId = DatabaseProvisioner::resolveRoleId($pdoDb, 'Superusuario');
        DatabaseProvisioner::createUser($pdoDb, 'root', 'root', $rolId, $dbName, $empresaId, true);
    }
}
