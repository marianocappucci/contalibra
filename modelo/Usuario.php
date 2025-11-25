<?php
class Usuario extends BaseModel {

    public function getByUsername($username) {
        $sql = "SELECT
                    u.id,
                    u.nombre,
                    u.username,
                    u.password,
                    u.rol_id,
                    u.activo,
                    u.base_datos,
                    u.must_change_password,
                    roles.nombre AS rol_nombre
                FROM usuarios u
                LEFT JOIN roles ON roles.id = u.rol_id
                WHERE u.username = ? AND u.activo = 1
                LIMIT 1";

        $stmt = $this->db->prepare($sql);
        $stmt->execute([$username]);
        return $stmt->fetch();
    }

    public function findActiveByUsername(string $username, ?string $baseDatos = null): array
    {
        $sql = "SELECT
                    u.id,
                    u.nombre,
                    u.username,
                    u.password,
                    u.rol_id,
                    u.activo,
                    u.base_datos,
                    u.must_change_password,
                    roles.nombre AS rol_nombre
                FROM usuarios u
                LEFT JOIN roles ON roles.id = u.rol_id
                WHERE u.username = ? AND u.activo = 1";

        $params = [$username];

        if (!empty($baseDatos)) {
            $sql .= " AND u.base_datos = ?";
            $params[] = $baseDatos;
        }

        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);

        return $stmt->fetchAll();
    }

    public function getById($id)
    {
        $sql = "SELECT
                    u.id,
                    u.nombre,
                    u.username,
                    u.password,
                    u.rol_id,
                    u.activo,
                    u.base_datos,
                    u.must_change_password,
                    roles.nombre AS rol_nombre
                FROM usuarios u
                LEFT JOIN roles ON roles.id = u.rol_id
                WHERE u.id = ? AND u.activo = 1
                LIMIT 1";

        $stmt = $this->db->prepare($sql);
        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    /**
     * Recupera un usuario desde la base maestra (contadb) sin depender de la
     * base de datos del tenant que esté activa en la sesión.
     */
    public function getByIdFromDefault(int $id)
    {
        $connection = Database::getDefaultStandaloneConnection();
        $stmt = $connection->prepare(
            "SELECT
                    u.id,
                    u.nombre,
                    u.username,
                    u.password,
                    u.rol_id,
                    u.activo,
                    u.base_datos,
                    u.must_change_password,
                    roles.nombre AS rol_nombre
                FROM usuarios u
                LEFT JOIN roles ON roles.id = u.rol_id
                WHERE u.id = ? AND u.activo = 1
                LIMIT 1"
        );

        $stmt->execute([$id]);
        return $stmt->fetch();
    }

    public function getAll() {
        $sql = "SELECT
                    u.id,
                    u.nombre,
                    u.username,
                    u.password,
                    u.rol_id,
                    u.activo,
                    u.base_datos,
                    u.must_change_password,
                    roles.nombre AS rol_nombre
                FROM usuarios u
                LEFT JOIN roles ON roles.id = u.rol_id";
        return $this->db->query($sql)->fetchAll();
    }

    public function getRoles() {
        $sql = "SELECT id, nombre FROM roles";
        return $this->db->query($sql)->fetchAll();
    }

    public function create(array $data) {
        $this->assertUsernameIsUnique($data['username']);

       $stmt = $this->db->prepare("INSERT INTO usuarios(nombre, username, password, rol_id, activo, base_datos, must_change_password)
                                    VALUES(?,?,?,?,?,?,?)");
        return $stmt->execute([
            $data['nombre'],
            $data['username'],
            $data['password'],
            $data['rol_id'],
            $data['activo'],
            $data['base_datos'],
            empty($data['must_change_password']) ? 0 : 1
        ]);
    }

    public function updatePassword(int $id, string $hashedPassword): bool
    {
        $stmt = $this->db->prepare("UPDATE usuarios SET password=? WHERE id=?");
        return $stmt->execute([$hashedPassword, $id]);
    }

    public function update($id, array $data)
    {
        $currentUser = $this->getById($id);
        $password = $data['password'] ?? '';

        if (empty($password)) {
            $password = $currentUser['password'] ?? '';
        } else {
            $info = password_get_info($password);
            if (($info['algo'] ?? 0) === 0) {
                $password = password_hash($password, PASSWORD_BCRYPT);
            }
        }

        $this->assertUsernameIsUnique($data['username'], (int) $id);

        $mustChangePassword = $data['must_change_password'] ?? ($currentUser['must_change_password'] ?? 0);

        $stmt = $this->db->prepare("UPDATE usuarios SET nombre=?, username=?, password=?, rol_id=?, activo=?, base_datos=?, must_change_password=? WHERE id=?");
        return $stmt->execute([
            $data['nombre'],
            $data['username'],
            $password,
            $data['rol_id'],
            $data['activo'],
            $data['base_datos'],
            $mustChangePassword ? 1 : 0,
            $id
        ]);
    }

    public function delete($id) {
        if ($this->usuarioTieneCajas((int) $id)) {
            throw new RuntimeException('No se puede eliminar el usuario porque tiene cajas asociadas.');
        }

        $stmt = $this->db->prepare("DELETE FROM usuarios WHERE id=?");
        return $stmt->execute([$id]);
    }

    private function usuarioTieneCajas(int $usuarioId): bool
    {
        $stmt = $this->db->prepare('SELECT COUNT(*) FROM cajas WHERE abierta_por = ?');
        $stmt->execute([$usuarioId]);

        return ((int) $stmt->fetchColumn()) > 0;
    }

    public function asignarBaseDatos(int $usuarioId, string $dbName): bool
    {
        $stmt = $this->db->prepare("UPDATE usuarios SET base_datos=? WHERE id=?");
        return $stmt->execute([$dbName, $usuarioId]);
    }

    private function assertUsernameIsUnique(string $username, ?int $ignoreId = null): void
    {
        $sql = 'SELECT COUNT(*) FROM usuarios WHERE username = ?';
        $params = [$username];

        if ($ignoreId !== null) {
            $sql .= ' AND id <> ?';
            $params[] = $ignoreId;
        }

        $stmt = $this->db->prepare($sql);
        $stmt->execute($params);

        if ((int) $stmt->fetchColumn() > 0) {
            throw new InvalidArgumentException('El nombre de usuario ya está en uso.');
        }
    }

    public function syncFromMaster(array $usuarioMaestro): bool
    {
        $stmt = $this->db->prepare(
            "INSERT INTO usuarios (id, nombre, username, password, rol_id, activo, base_datos, must_change_password)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        );

        return $stmt->execute([
            $usuarioMaestro['id'],
            $usuarioMaestro['nombre'] ?? '',
            $usuarioMaestro['username'] ?? '',
            $usuarioMaestro['password'] ?? '',
            $usuarioMaestro['rol_id'] ?? 1,
            $usuarioMaestro['activo'] ?? 1,
            $usuarioMaestro['base_datos'] ?? ($_SESSION['db_name'] ?? DB_NAME),
            $usuarioMaestro['must_change_password'] ?? 0,
        ]);
    }

    public function updatePasswordAndClearFlag(int $id, string $hashedPassword): bool
    {
        $stmt = $this->db->prepare('UPDATE usuarios SET password = ?, must_change_password = 0 WHERE id = ?');

        return $stmt->execute([$hashedPassword, $id]);
    }
}
