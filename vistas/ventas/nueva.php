<?php include __DIR__ . '/../layout/header.php'; ?>
<?php include __DIR__ . '/../layout/topbar.php'; ?>
<?php include __DIR__ . '/../layout/sidebar.php'; ?>

<style>
    :root {
        --accent: #f38064;
    }

    .nv-wrapper {
        padding: 10px;
    }

    .nv-card {
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        padding: 12px 14px;
        margin-bottom: 10px;
    }

    .nv-card-header {
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: .04em;
    }

    .nv-search-input {
        border-radius: 6px;
        border: 1px solid #ddd;
    }

    .nv-search-input:focus {
        border-color: var(--accent);
        box-shadow: 0 0 0 .15rem rgba(243,128,100,.25);
    }

    .nv-left-panel {
        height: calc(100vh - 110px);
        display: flex;
        flex-direction: column;
    }

    .nv-left-list {
        flex: 1;
        overflow-y: auto;
        margin-top: 8px;
        padding-right: 4px;
    }

    .nv-product-card {
        border-radius: 6px;
        border: 1px solid #eee;
        padding: 8px 10px;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: background-color .15s, box-shadow .15s;
        cursor: pointer;
    }

    .nv-product-card:hover {
        background: #fafafa;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }

    .nv-product-name {
        font-size: 0.85rem;
        font-weight: 600;
    }

    .nv-product-extra {
        font-size: 0.75rem;
        color: #888;
    }

    .nv-product-price {
        font-size: 0.85rem;
        font-weight: 600;
    }

    .nv-btn-plus {
        border-radius: 50%;
        width: 32px;
        height: 32px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: 1px solid var(--accent);
        color: var(--accent);
        background: #fff;
    }

    .nv-btn-plus:hover {
        background: var(--accent);
        color: #fff;
    }

    /* Panel derecha */

    .nv-right-panel {
        height: calc(100vh - 110px);
        display: flex;
        flex-direction: column;
    }

    .nv-client-header {
        background: #f5f5f5;
        border-radius: 8px 8px 0 0;
        padding: 10px 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #e0e0e0;
    }

    .nv-client-title {
        font-size: 0.9rem;
        font-weight: 600;
    }

    .nv-client-name-input {
        border-radius: 4px;
        border: 1px solid #ccc;
        padding: 4px 8px;
        width: 260px;
        font-size: 0.85rem;
    }

    .nv-cart-table-wrapper {
        flex: 1;
        overflow-y: auto;
        border: 1px solid #e0e0e0;
        border-top: none;
        border-radius: 0 0 8px 8px;
        background: #fff;
    }

    .nv-cart-table thead {
        background: #fafafa;
        font-size: 0.8rem;
    }

    .nv-cart-table th,
    .nv-cart-table td {
        padding: 6px 8px;
        vertical-align: middle;
        font-size: 0.8rem;
    }

    .nv-cart-table input.form-control-sm {
        padding: 3px 6px;
        font-size: 0.8rem;
        height: 28px;
    }

    .nv-summary-card {
        margin-top: 8px;
        padding: 10px 14px;
        background: #ffffff;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        font-size: 0.8rem;
    }

    .nv-summary-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
    }

    .nv-summary-row span:last-child {
        font-weight: 600;
    }

    .nv-pay-buttons {
        margin-top: 8px;
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }

    .nv-pay-btn {
        border-radius: 6px;
        border: 1px solid var(--accent);
        padding: 6px 8px;
        flex: 1 1 120px;
        font-size: 0.8rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: var(--accent);
        background: #fff;
    }

    .nv-pay-btn i {
        font-size: 1.1rem;
        margin-bottom: 2px;
    }

    .nv-pay-btn:hover {
        background: var(--accent);
        color: #fff;
    }

    .nv-pay-btn-main {
        background: #555;
        color: #fff;
        border-color: #555;
    }

    .nv-pay-btn-main span:last-child {
        font-weight: 700;
    }

    .nv-pay-btn-main:hover {
        background: #333;
    }

    .nv-pay-btn-main .nv-total-cobrar {
        font-size: 0.95rem;
    }

    .nv-submit-row {
        margin-top: 8px;
        display: flex;
        justify-content: flex-end;
        gap: 8px;
    }

    .nv-submit-row button {
        min-width: 130px;
    }

    /* Color de iconos global (sidebar + panel principal) */
    .bi {
        color: var(--accent);
    }

    .btn .bi {
        color: inherit; /* para que en botones use el color del botón */
    }
</style>

<div id="content">
    <div class="container-fluid nv-wrapper">

        <div class="row mb-2">
            <div class="col-12 d-flex justify-content-between align-items-center">
                <h4 class="mb-0">Nueva venta</h4>
                <small class="text-muted">Contalibra Punto de Venta</small>
            </div>
        </div>

        <form method="post" action="index.php?controller=Venta&action=nueva" id="formVenta">

            <div class="row">
                <!-- COLUMNA IZQUIERDA: LISTA DE PRODUCTOS -->
                <div class="col-md-4 nv-left-panel">

                    <div class="nv-card">
                        <div class="d-flex align-items-center mb-2">
                            <input type="text" id="buscadorProductos" class="form-control nv-search-input" placeholder="Buscar por nombre, ID, SKU">
                            <button type="button" class="btn btn-light ms-2">
                                <i class="bi bi-search"></i>
                            </button>
                        </div>
                        <div class="d-flex justify-content-between small text-muted">
                            <span>Ver todo</span>
                            <span id="lblCantidadProductos"></span>
                        </div>
                    </div>

                    <div class="nv-left-list" id="listaProductos">
                        <!-- aquí se cargan los productos vía JS -->
                    </div>
                </div>

                <!-- COLUMNA DERECHA: CARRITO + RESUMEN -->
                <div class="col-md-8 nv-right-panel">

                    <!-- CABECERA CLIENTE -->
                    <div class="nv-client-header">
                        <div class="nv-client-title">Consumidor final</div>
                        <div class="d-flex align-items-center">
                            <input type="text" name="cliente" value="Consumidor Final" class="nv-client-name-input">
                            <span class="ms-3 small text-muted">Minorista</span>
                        </div>
                    </div>

                    <!-- TABLA CARRITO -->
                    <div class="nv-cart-table-wrapper">
                        <table class="table nv-cart-table mb-0" id="tablaItems">
                            <thead>
                                <tr>
                                    <th style="width: 70px;">Cant.</th>
                                    <th>Descripción</th>
                                    <th style="width: 110px;">Precio</th>
                                    <th style="width: 110px;">Subtotal</th>
                                    <th style="width: 40px;"></th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- filas se agregan por JS -->
                            </tbody>
                        </table>
                    </div>

                    <!-- RESUMEN + BOTONES DE PAGO -->
                    <div class="nv-summary-card mt-2">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="nv-summary-row">
                                    <span>Vendedor</span>
                                    <span>Sin vendedor</span>
                                </div>
                                <div class="nv-summary-row">
                                    <span>Cantidad de ítems</span>
                                    <span id="lblCantItems">0</span>
                                </div>
                                <div class="nv-summary-row">
                                    <span>Descuento / recargo</span>
                                    <span>$ 0,00</span>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="nv-summary-row">
                                    <span>Subtotal neto</span>
                                    <span id="lblSubtotal">$ 0,00</span>
                                </div>
                                <div class="nv-summary-row">
                                    <span>IVA</span>
                                    <span id="lblIva">$ 0,00</span>
                                </div>
                                <div class="nv-summary-row">
                                    <span>Total</span>
                                    <span id="lblTotal">$ 0,00</span>
                                </div>
                            </div>
                        </div>

                        <!-- hidden totals para backend -->
                        <input type="hidden" id="subtotal" name="subtotal" value="0">
                        <input type="hidden" id="iva" name="iva" value="0">
                        <input type="hidden" id="total" name="total" value="0">

                        <div class="nv-pay-buttons">
                            <button type="button" class="nv-pay-btn">
                                <i class="bi bi-cash"></i>
                                <span>Efectivo caja</span>
                            </button>
                            <button type="button" class="nv-pay-btn">
                                <i class="bi bi-credit-card"></i>
                                <span>MercadoPago</span>
                            </button>
                            <button type="button" class="nv-pay-btn">
                                <i class="bi bi-credit-card-2-back"></i>
                                <span>Tarjeta crédito</span>
                            </button>
                            <button type="button" class="nv-pay-btn">
                                <i class="bi bi-three-dots"></i>
                                <span>Otros</span>
                            </button>
                            <button type="submit" class="nv-pay-btn nv-pay-btn-main">
                                <span>Cobrar</span>
                                <span class="nv-total-cobrar" id="lblCobrar">$ 0,00</span>
                            </button>
                        </div>
                    </div>

                    <div class="nv-submit-row">
                        <a href="index.php?controller=Venta&action=index" class="btn btn-outline-secondary btn-sm">Volver</a>
                        <button type="submit" class="btn btn-success btn-sm">Confirmar venta</button>
                    </div>

                </div><!-- fin col derecha -->
            </div><!-- row -->

        </form>
    </div>
</div>

<script>
    // ========= UTILIDADES DE FORMATO =========
    function formatMoney(n) {
        n = parseFloat(n) || 0;
        return "$ " + n.toFixed(2);
    }

    // ========= CARGA DE PRODUCTOS IZQUIERDA =========
    function cargarProductos(term = "") {
        const contenedor = document.getElementById("listaProductos");
        contenedor.innerHTML = "<div class='text-muted small px-2'>Cargando productos...</div>";

        fetch("index.php?controller=Producto&action=buscarAjax&term=" + encodeURIComponent(term))
            .then(r => r.json())
            .then(data => {
                contenedor.innerHTML = "";
                document.getElementById("lblCantidadProductos").textContent = data.length + " productos";
                if (!data.length) {
                    contenedor.innerHTML = "<div class='text-muted small px-2'>No se encontraron productos</div>";
                    return;
                }

                data.forEach(prod => {
                    const card = document.createElement("div");
                    card.className = "nv-product-card";

                    card.innerHTML = `
                        <div>
                            <div class="nv-product-name">${prod.nombre}</div>
                            <div class="nv-product-extra">Stock: ${prod.stock ?? 0}</div>
                            <div class="nv-product-price">${formatMoney(prod.precio)}</div>
                        </div>
                        <button type="button" class="nv-btn-plus btnAgregarProducto"
                                data-id="${prod.id}" data-nombre="${prod.nombre}"
                                data-precio="${prod.precio}" data-stock="${prod.stock ?? 0}">
                            <i class="bi bi-plus-lg"></i>
                        </button>
                    `;

                    contenedor.appendChild(card);
                });
            })
            .catch(() => {
                contenedor.innerHTML = "<div class='text-danger small px-2'>Error al cargar productos</div>";
            });
    }

    document.getElementById("buscadorProductos").addEventListener("keyup", function () {
        const term = this.value.trim();
        cargarProductos(term);
    });

    // ========= CARRITO =========
    function recalcularLinea(fila) {
        const cant = parseFloat(fila.querySelector(".cantidad").value) || 0;
        const precio = parseFloat(fila.querySelector(".precio_unitario").value) || 0;
        const total = cant * precio;

        fila.querySelector(".total_linea").textContent = formatMoney(total);
        fila.querySelector(".total_linea_input").value = total.toFixed(2);

        actualizarTotales();
    }

    function actualizarTotales() {
        let subtotal = 0;
        const filas = document.querySelectorAll("#tablaItems tbody tr");
        filas.forEach(f => {
            subtotal += parseFloat(f.querySelector(".total_linea_input").value) || 0;
        });

        const iva = subtotal * 0.21;
        const total = subtotal + iva;

        document.getElementById("lblCantItems").textContent = filas.length;
        document.getElementById("lblSubtotal").textContent = formatMoney(subtotal);
        document.getElementById("lblIva").textContent = formatMoney(iva);
        document.getElementById("lblTotal").textContent = formatMoney(total);
        document.getElementById("lblCobrar").textContent = formatMoney(total);

        document.getElementById("subtotal").value = subtotal.toFixed(2);
        document.getElementById("iva").value = iva.toFixed(2);
        document.getElementById("total").value = total.toFixed(2);
    }

    function reindexarFilas() {
        const filas = document.querySelectorAll("#tablaItems tbody tr");
        filas.forEach((fila, idx) => {
            fila.querySelector(".producto_id").name       = `items[${idx}][producto_id]`;
            fila.querySelector(".cantidad").name          = `items[${idx}][cantidad]`;
            fila.querySelector(".precio_unitario").name   = `items[${idx}][precio_unitario]`;
            fila.querySelector(".total_linea_input").name = `items[${idx}][total]`;
        });
    }

    function agregarProductoAlCarrito(prod) {
        const tbody = document.querySelector("#tablaItems tbody");

        // ¿Ya existe ese producto en el carrito?
        let fila = tbody.querySelector(`tr[data-producto-id="${prod.id}"]`);
        if (fila) {
            const cantInput = fila.querySelector(".cantidad");
            cantInput.value = (parseFloat(cantInput.value) || 0) + 1;
            recalcularLinea(fila);
            return;
        }

        // Nueva fila
        fila = document.createElement("tr");
        fila.className = "fila-item";
        fila.dataset.productoId = prod.id;

        fila.innerHTML = `
            <td>
                <input type="number" min="1" step="1" value="1"
                    class="form-control form-control-sm cantidad">
            </td>
            <td>
                <input type="hidden" class="producto_id" value="${prod.id}">
                <div class="fw-semibold small descripcion">${prod.nombre}</div>
            </td>
            <td>
                <input type="number" step="0.01"
                    class="form-control form-control-sm precio_unitario" value="${prod.precio}">
            </td>
            <td>
                <span class="total_linea">${formatMoney(prod.precio)}</span>
                <input type="hidden" class="total_linea_input" value="${parseFloat(prod.precio).toFixed(2)}">
            </td>
            <td class="text-center">
                <button type="button" class="btn btn-sm btn-outline-danger btnEliminarFila">
                    <i class="bi bi-x-lg"></i>
                </button>
            </td>
        `;

        tbody.appendChild(fila);
        reindexarFilas();
        recalcularLinea(fila);
    }

    // Click en lista de productos (botón +)
    document.getElementById("listaProductos").addEventListener("click", function (e) {
        const btn = e.target.closest(".btnAgregarProducto");
        if (!btn) return;

        const prod = {
            id: btn.dataset.id,
            nombre: btn.dataset.nombre,
            precio: btn.dataset.precio,
            stock: btn.dataset.stock
        };

        agregarProductoAlCarrito(prod);
    });

    // Cambios en cantidad o precio dentro del carrito
    document.querySelector("#tablaItems").addEventListener("input", function (e) {
        if (e.target.classList.contains("cantidad") || e.target.classList.contains("precio_unitario")) {
            const fila = e.target.closest("tr");
            recalcularLinea(fila);
        }
    });

    // Eliminar fila
    document.querySelector("#tablaItems").addEventListener("click", function (e) {
        if (!e.target.closest(".btnEliminarFila")) return;
        const fila = e.target.closest("tr");
        fila.remove();
        reindexarFilas();
        actualizarTotales();
    });

    // Carga inicial
    cargarProductos("");
</script>

<?php include __DIR__ . '/../layout/footer.php'; ?>
