document.addEventListener('DOMContentLoaded', function () {
  const tabla = document.getElementById('tablaItems');
  if (!tabla) return;

  function recalcular() {
    let subtotal = 0;
    tabla.querySelectorAll('tbody tr').forEach(tr => {
      const cant = parseFloat(tr.querySelector('.cantidad').value) || 0;
      const pu = parseFloat(tr.querySelector('.precio_unitario').value) || 0;
      const total = cant * pu;
      tr.querySelector('.total_linea').innerText = total.toFixed(2);
      subtotal += total;
    });
    const iva = subtotal * 0.21;
    const total = subtotal + iva;
    document.getElementById('lblSubtotal').innerText = subtotal.toFixed(2);
    document.getElementById('lblIva').innerText = iva.toFixed(2);
    document.getElementById('lblTotal').innerText = total.toFixed(2);
  }

  tabla.addEventListener('change', function (e) {
    if (e.target.classList.contains('producto-select')) {
      const precio = parseFloat(e.target.selectedOptions[0].dataset.precio || 0);
      const tr = e.target.closest('tr');
      tr.querySelector('.precio_unitario').value = precio.toFixed(2);
    }
    if (e.target.classList.contains('cantidad') || e.target.classList.contains('precio_unitario')) {
      recalcular();
    }
  });

  document.getElementById('btnAgregarFila').addEventListener('click', function(){
    const tbody = tabla.querySelector('tbody');
    const idx = tbody.querySelectorAll('tr').length;
    const nueva = tbody.querySelector('tr').cloneNode(true);
    nueva.querySelectorAll('input, select').forEach(el => {
      el.name = el.name.replace(/items\[\d+\]/, 'items['+idx+']');
      if (el.tagName === 'SELECT') {
        el.selectedIndex = 0;
      } else {
        el.value = el.classList.contains('cantidad') ? '1' : '0';
      }
    });
    nueva.querySelector('.total_linea').innerText = '0.00';
    tbody.appendChild(nueva);
  });

  tabla.addEventListener('click', function(e){
    if (e.target.classList.contains('btnEliminarFila')) {
      const tbody = tabla.querySelector('tbody');
      if (tbody.querySelectorAll('tr').length > 1) {
        e.target.closest('tr').remove();
        recalcular();
      }
    }
  });

  recalcular();
});
