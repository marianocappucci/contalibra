<?php include __DIR__.'/../layout/header.php'; ?>
<?php include __DIR__.'/../layout/topbar.php'; ?>
<?php include __DIR__.'/../layout/sidebar.php'; ?>
<div id="content" class="content p-4">
<h3>Logs del Sistema</h3>
<table class="table table-striped">
<thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Módulo</th><th>IP</th></tr></thead>
<tbody>
<?php while($l=$logs->fetch_assoc()): ?>
<tr>
<td><?= $l['fecha'] ?></td>
<td><?= $l['usuario_nombre'] ?></td>
<td><?= $l['accion'] ?></td>
<td><?= $l['modulo'] ?></td>
<td><?= $l['ip'] ?></td>
</tr>
<?php endwhile; ?>
</tbody>
</table>
</div>
<?php include __DIR__.'/../layout/footer.php'; ?>