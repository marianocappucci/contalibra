<?php include __DIR__ . '/../layout/header.php'; ?>

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">

<style>
    .contexto-container {
        max-width: 680px;
        margin: 60px auto;
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
        padding: 32px;
    }
    .contexto-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 18px;
    }
    .contexto-header i {
        font-size: 1.8rem;
        color: #0d6efd;
    }
    .contexto-badge {
        background: #e9f2ff;
        color: #0d6efd;
        border-radius: 6px;
        padding: 6px 10px;
        font-weight: 600;
        font-size: 0.95rem;
    }
</style>

<div class="contexto-container">
    <div class="contexto-header">
        <i class="bi bi-building-check"></i>
        <div>
            <h4 class="mb-0">Selecciona la sucursal y el punto de venta</h4>
            <small class="text-muted">Empresa autenticada: <?php echo htmlspecialchars($empresa['nombre']); ?></small>
        </div>
        <span class="ms-auto contexto-badge">Paso requerido</span>
    </div>

    <?php if (!empty($error)): ?>
        <div class="alert alert-danger"><?php echo htmlspecialchars($error); ?></div>
    <?php endif; ?>

    <?php if (empty($sucursales)): ?>
        <div class="alert alert-warning">
            No hay sucursales configuradas para esta empresa. Crea una antes de continuar.
        </div>
    <?php else: ?>
        <form method="post" action="index.php?controller=Contexto&action=seleccionar">
            <div class="mb-3">
                <label class="form-label">Sucursal</label>
                <select name="sucursal_id" id="sucursal_id" class="form-select" required>
                    <option value="">Elige una sucursal</option>
                    <?php foreach ($sucursales as $sucursal): ?>
                        <option value="<?php echo (int) $sucursal['id']; ?>">
                            <?php echo htmlspecialchars($sucursal['nombre']); ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div class="mb-3">
                <label class="form-label">Punto de venta</label>
                <select name="punto_venta_id" id="punto_venta_id" class="form-select" required>
                    <option value="">Primero elige una sucursal</option>
                </select>
                <div class="form-text">Solo se muestran los puntos de venta de la sucursal seleccionada.</div>
            </div>

            <div class="d-flex justify-content-between align-items-center mt-4">
                <div class="text-muted small">
                    El dashboard se mostrará una vez guardes la selección.
                </div>
                <button type="submit" class="btn btn-primary">Continuar al dashboard</button>
            </div>
        </form>
    <?php endif; ?>
</div>

<script>
    const sucursales = <?php echo json_encode($sucursales, JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP); ?>;
    const sucursalSelect = document.getElementById('sucursal_id');
    const puntoVentaSelect = document.getElementById('punto_venta_id');

    function renderPuntosVenta(sucursalId) {
        puntoVentaSelect.innerHTML = '';

        if (!sucursalId) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'Primero elige una sucursal';
            puntoVentaSelect.appendChild(option);
            return;
        }

        const sucursal = sucursales.find(s => parseInt(s.id, 10) === parseInt(sucursalId, 10));

        if (!sucursal || !sucursal.puntos_venta || sucursal.puntos_venta.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'La sucursal no tiene puntos de venta activos';
            puntoVentaSelect.appendChild(option);
            return;
        }

        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = 'Elige un punto de venta';
        puntoVentaSelect.appendChild(placeholder);

        sucursal.puntos_venta.forEach(pv => {
            const option = document.createElement('option');
            option.value = pv.id;
            option.textContent = pv.nombre + (pv.codigo ? ` (Código ${pv.codigo})` : '');
            puntoVentaSelect.appendChild(option);
        });
    }

    sucursalSelect.addEventListener('change', (event) => {
        renderPuntosVenta(event.target.value);
    });
</script>

<?php include __DIR__ . '/../layout/footer.php'; ?>
