
<div class="mb-3 d-flex gap-2">
<button onclick="imprimirReporte()" class="btn btn-secondary"><i class="bi bi-printer"></i> Imprimir</button>
<a href="index.php?controller=Reporte&action=exportarVentas" class="btn btn-success"><i class="bi bi-file-earmark-excel"></i> Exportar a Excel</a>
</div>
<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<div id="content">

<div class="container">
  <h3>Reporte de ventas</h3>
  <form class="row g-3 mb-3" method="get">
    <input type="hidden" name="controller" value="Reporte">
    <input type="hidden" name="action" value="ventas">
    <div class="col-md-3">
      <label class="form-label">Desde</label>
      <input type="date" name="desde" class="form-control" value="<?php echo htmlspecialchars($desde ?? ''); ?>">
    </div>
    <div class="col-md-3">
      <label class="form-label">Hasta</label>
      <input type="date" name="hasta" class="form-control" value="<?php echo htmlspecialchars($hasta ?? ''); ?>">
    </div>
    <div class="col-md-3 align-self-end">
      <button class="btn btn-primary">Filtrar</button>
    </div>
  </form>
<div class="mb-3 d-flex gap-2">
    <button onclick="window.print()" class="btn btn-secondary">
        <i class="bi bi-printer"></i> Imprimir
    </button>

    <a href="index.php?controller=Reporte&action=exportarVentas" class="btn btn-success">
        <i class="bi bi-file-earmark-excel"></i> Exportar a Excel
    </a>
</div>

  <div id="area_reporte">
    <div style="text-align: center; margin-bottom: 10px;">
    
       
    </div>
<table class="table table-striped">
    <thead>
      <tr>
        <th>ID</th>
        <th>Fecha</th>
        <th>Cliente</th>
        <th>Total</th>
        <th>Estado</th>
      </tr>
    </thead>
    <tbody>
      <?php 
      $totalGeneral = 0;
      foreach ($ventas as $v): 
        $totalGeneral += $v['total'];
      ?>
      <tr>
        <td><?php echo $v['id']; ?></td>
        <td><?php echo $v['fecha']; ?></td>
        <td><?php echo htmlspecialchars($v['cliente']); ?></td>
        <td>$<?php echo number_format($v['total'], 2); ?></td>
        <td><?php echo $v['estado']; ?></td>
      </tr>
      <?php endforeach; ?>
    </tbody>
    <tfoot>
      <tr>
        <th colspan="3" class="text-end">Total general:</th>
        <th>$<?php echo number_format($totalGeneral, 2); ?></th>
        <th></th>
      </tr>
    </tfoot>
  </table>
</div>
</div>
</div> <!-- cierre de content -->

<?php include __DIR__ . '/../layout/footer.php'; ?>

<script>
function imprimirReporte() {
    var contenido = document.getElementById("area_reporte").innerHTML;
    var ventana = window.open("", "PRINT", "height=800,width=1000");
    ventana.document.write(`
        <html><head><title>Reporte de Ventas - Contalibra</title>
        <style>
        body{font-family:Montserrat,Arial;margin:30px;}
        h2{text-align:center;margin:0;}
        img{display:block;margin:0 auto 10px auto;}
        table{width:100%;border-collapse:collapse;margin-top:15px;}
        table,th,td{border:1px solid #444;}
        th{background:#eee;padding:8px;}
        td{padding:6px;}
        </style></head><body>${contenido}</body></html>`);
    ventana.document.close(); ventana.focus(); ventana.print(); ventana.close();
}
</script>
