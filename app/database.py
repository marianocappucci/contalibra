# Infraestructura compartida y módulos por dominio, extraídos de este archivo
# como parte del split en módulos lógicos (Fase 3 de LibraCore, sub-paso
# previo dentro de cada producto, sin cambiar comportamiento — ver
# wiki/entities/libracore.md). Re-exportados acá para que los call sites
# existentes (`db.get_connection()`, `db.DB_PATH`, `db.create_usuario(...)`,
# etc.) no cambien una línea.
from libracore.db.schema import init_core_schema
from libracore.db.clients import sincronizar_parties_de_clientes
from libracommerce.db.schema import init_schema as init_commerce_schema
from app.db_core import _AR_TZ, _ar_now, _DATA_DIR, DB_PATH, get_connection  # noqa: F401
from app.db_usuarios import (  # noqa: F401
    _hash_password,
    _verify_password,
    _DUMMY_PASSWORD_HASH,
    create_usuario,
    get_usuario_by_username,
    get_usuario_by_id,
    get_all_usuarios,
    update_usuario,
    update_usuario_password,
    delete_usuario,
    check_usuario_credentials,
    ensure_admin_user,
    # Recuperacion de contrasena por correo (libraauth v0.5.0).
    solicitar_reset_password,
    resetear_password_con_token,
    EmailNotConfigured,
    InvalidResetToken,
)
from app.db_tesoreria import (  # noqa: F401
    get_all_cuentas_tesoreria,
    get_cuenta_tesoreria,
    create_cuenta_tesoreria,
    update_cuenta_tesoreria,
    delete_cuenta_tesoreria,
    get_movimientos_tesoreria,
    create_movimiento_tesoreria,
    create_transferencia_tesoreria,
    delete_movimiento_tesoreria,
    get_resumen_tesoreria,
)
from app.db_caja import (  # noqa: F401
    MEDIOS_PAGO_LABELS,
    get_all_cajas,
    get_caja_config,
    get_default_caja_id,
    create_caja_config,
    update_caja_config,
    set_default_caja,
    delete_caja_config,
    create_caja_movimiento,
    get_caja_movimientos,
    get_caja_resumen,
    get_cobro_factura,
    get_cobros_factura,
    delete_caja_movimiento,
)
from app.db_egresos import (  # noqa: F401
    get_categorias_egreso,
    create_categoria_egreso,
    delete_categoria_egreso,
    get_all_proveedores,
    get_proveedor,
    search_proveedores,
    create_proveedor,
    update_proveedor,
    delete_proveedor,
    create_egreso,
    get_egreso,
    get_all_egresos,
    get_resumen_egresos,
    delete_egreso,
    get_pagos_egreso,
    create_pago_egreso,
)
from app.db_modulos import get_modulos, apply_plan  # noqa: F401
from app.db_listas_precio import (  # noqa: F401
    get_all_listas_precio,
    get_lista_precio,
    create_lista_precio,
    update_lista_precio,
    delete_lista_precio,
    get_lista_precio_items,
    get_precio_en_lista,
    get_precios_lista_dict,
    save_lista_precio_items,
    apply_porcentaje_lista,
    importar_precios_lista,
)
from app.db_turnos import (  # noqa: F401
    create_turno,
    get_turno_activo,
    get_turno_activo_any,
    get_all_turnos,
    get_turno,
    get_resumen_turno,
    cerrar_turno,
    vincular_venta_turno,
)
from app.db_dashboard import get_dashboard_data  # noqa: F401
from app.db_logs import (  # noqa: F401
    get_actividad_log,
    get_actividad_count,
    registrar_auth_event,
    get_auth_log,
    contar_login_fallidos_recientes,
)
from app.db_arca_config import (  # noqa: F401
    crear_arca_config,
    obtener_arca_config,
    obtener_todas_arca_configs,
    actualizar_arca_config,
    eliminar_arca_config,
)
from app.db_cuenta_corriente import (  # noqa: F401
    get_cc_saldo,
    get_cc_movimientos,
    get_clientes_con_saldo_cc,
    create_cc_pago,
    delete_cc_pago,
)
from app.db_libros_iva import get_facturas_para_iva, get_egresos_para_iva  # noqa: F401
from app.db_reportes import (  # noqa: F401
    get_reporte_ventas,
    get_reporte_medios_pago,
    get_reporte_productos_top,
    get_reporte_caja,
    get_reporte_caja_medios,
    get_reporte_stock_bajo,
    get_reporte_resumen,
)
from app.db_productos import (  # noqa: F401
    get_all_depositos,
    get_deposito,
    get_default_deposito_id,
    create_deposito,
    update_deposito,
    set_default_deposito,
    delete_deposito,
    get_stock_por_deposito,
    get_stock_producto_todos_depositos,
    transferir_stock,
    get_categorias_producto,
    create_categoria_producto,
    delete_categoria_producto,
    create_producto,
    get_all_productos,
    get_producto,
    get_producto_by_codigo,
    update_producto,
    delete_producto,
)
from app.db_stock import (  # noqa: F401
    add_movimiento_stock,
    get_stock_actual,
    get_stock_todos,
    get_movimientos_stock,
    ajustar_stock,
    descontar_stock_venta,
)
from app.db_clients import (  # noqa: F401
    create_client,
    get_all_clients,
    get_all_clients_including_inactive,
    get_client,
    desactivar_cliente,
    activar_cliente,
    tiene_presupuestos_aprobados,
    get_facturas_by_client,
    update_client,
    toggle_auto_facturar,
    delete_client,
    get_client_by_email,
    get_client_by_cuit,
)
from app.db_remitos_presupuestos import (  # noqa: F401
    get_next_remito_number,
    create_remito,
    update_remito_pdf_path,
    get_all_remitos,
    get_remito,
    get_remitos_by_client,
    search_remitos,
    get_next_presupuesto_number,
    auto_vencimiento_presupuestos,
    create_presupuesto,
    update_presupuesto_pdf_path,
    update_presupuesto_status,
    update_presupuesto_remito_id,
    get_all_presupuestos,
    get_presupuestos_count_by_estado,
    get_presupuesto,
    get_presupuestos_by_client,
    search_presupuestos,
    delete_remito,
    delete_presupuesto,
    update_remito,
    update_presupuesto,
)
from app.db_facturas import (  # noqa: F401
    get_next_factura_numero,
    create_factura,
    get_all_facturas,
    get_facturas_filtradas,
    get_factura,
    update_factura_cae,
    update_factura_pdf_path,
    search_facturas,
    get_notas_de_factura,
    get_nc_de_factura,
    get_nd_de_factura,
    get_factura_por_tipo_pv_nro,
    delete_factura,
)
from app.db_mp import (  # noqa: F401
    get_mp_pago,
    create_mp_pago,
    get_mp_pago_by_id,
    get_mp_pagos_by_estado,
    get_mp_pagos_historial,
    update_mp_pago_estado,
    crear_alias_facturacion,
    get_alias_facturacion_by_cliente,
    eliminar_alias_facturacion,
    get_cliente_por_alias_pago,
    resolver_cliente_pago,
    get_mp_movimiento_by_mp_id,
    create_mp_movimiento,
    get_mp_movimiento_by_id,
    get_mp_movimientos_by_estado,
    get_mp_movimientos_historial,
    update_mp_movimiento_datos,
    update_mp_movimiento_estado,
    get_mp_pending_count,
    vincular_mp_pago_cliente,
)
from app.db_ventas import (  # noqa: F401
    get_next_venta_numero,
    create_venta,
    add_venta_pago,
    crear_venta_directa,
    get_all_ventas,
    get_venta,
    anular_venta,
    vincular_venta_factura,
    vincular_venta_remito,
    set_venta_mp_order,
    set_venta_mp_payment,
    get_venta_by_mp_order,
    add_venta_pago_referencia_mp,
)


def _migrar_ventas_pagos_a_sales(conn):
    """Repunta la FK de `ventas_pagos` de `ventas(id)` (schema de LibraCore)
    a `sales(id)` (LibraCommerce), que es donde viven las ventas de
    Contalibra desde P7.

    El schema compartido de LibraCore crea la tabla con `REFERENCES
    ventas(id)` — correcto para Restolibra, pero acá cada INSERT de un pago
    fallaba con FOREIGN KEY constraint (el pragma foreign_keys está activo
    por conexión desde libracore). En la base del cliente real la FK ya se
    repuntó durante P7; esta migración existe para los otros dos casos, que
    la suite encontró rotos el 2026-07-30: la base de dev del VPS (quedó con
    la FK vieja) y cualquier instalación desde cero (init_db recreaba la FK
    vieja). Idempotente: si la FK ya apunta a `sales`, no hace nada.

    `ventas_pagos` no tiene tablas hijas (verificado en los schemas de los
    dos motores), así que el rebuild no pisa la trampa del RENAME de SQLite
    que reescribe las FK de las hijas (ver P8 de Restolibra). Los ids de
    `sales` preservan los de la vieja `ventas` (así migró P7), por lo que
    las filas copiadas siguen siendo válidas contra la tabla nueva.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='ventas_pagos'"
    ).fetchone()
    if not row or "REFERENCES sales(" in row[0]:
        return

    # Filas que no tienen su venta en `sales`. En una base al día no hay
    # ninguna (P7 movió los datos preservando los ids) y en una base nueva
    # la tabla está vacía. Aparecen sólo en un entorno a medio migrar: el
    # código escribe en `sales` pero los datos viejos quedaron en `ventas`.
    #
    # NO se descartan: son registros de dinero. Se copian igual y se avisa,
    # porque quedan referenciando una venta inexistente y eso tiene que ser
    # una decisión de alguien, no un efecto silencioso de un deploy.
    huerfanas = conn.execute("""
        SELECT COUNT(*) FROM ventas_pagos vp
        LEFT JOIN sales s ON s.id = vp.venta_id
        WHERE s.id IS NULL
    """).fetchone()[0]
    if huerfanas:
        print(
            f"[ADVERTENCIA] ventas_pagos: {huerfanas} fila(s) referencian una venta "
            "que no está en `sales` (entorno a medio migrar de P7). Se conservan "
            "tal cual, pero quedan como referencias colgadas: revisar a mano.",
            flush=True,
        )

    # El pragma es por conexión y no se puede tocar dentro de una
    # transacción: se apaga, se reconstruye y se vuelve a encender.
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        conn.execute("ALTER TABLE ventas_pagos RENAME TO ventas_pagos_old")
        conn.execute("""
            CREATE TABLE ventas_pagos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id   INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
                medio      TEXT NOT NULL,
                monto      REAL NOT NULL,
                referencia TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            INSERT INTO ventas_pagos (id, venta_id, medio, monto, referencia, created_at)
            SELECT id, venta_id, medio, monto, referencia, created_at
            FROM ventas_pagos_old
        """)
        conn.execute("DROP TABLE ventas_pagos_old")
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def init_db():
    with get_connection() as conn:
        init_core_schema(conn)
        # Catálogo/stock/ventas viven en las tablas de LibraCommerce desde
        # P7 (ver db_productos.py). Conviven en el MISMO archivo SQLite que
        # el resto de Contalibra, a propósito: `crear_venta_directa` cruza
        # ambos motores en una única transacción atómica.
        init_commerce_schema(conn)
        _migrar_ventas_pagos_a_sales(conn)

        # Depósito por defecto: LibraCore hace el equivalente con la caja
        # (schema.py seed-ea una con es_default=1), pero LibraCommerce no
        # seed-ea ninguna location — y sin al menos una, cualquier
        # movimiento de stock revienta con NOT NULL location_id (lo
        # encontró la suite el 2026-07-30 sobre una base desde cero). Solo
        # si no existe ninguna: las instancias reales ya tienen las suyas.
        existe_location = conn.execute("SELECT 1 FROM locations LIMIT 1").fetchone()
        if not existe_location:
            conn.execute(
                "INSERT INTO locations (name, description, is_default, active)"
                " VALUES ('Depósito principal', '', 1, 1)"
            )

        # Referencias cruzadas entre la venta (LibraCommerce) y contextos que
        # no son suyos: facturación/remitos y turno de caja (LibraCore) y
        # MercadoPago. No van dentro de `sales` para no meter dominio ajeno en
        # el motor genérico — ver db_ventas.py.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS venta_links (
                venta_id      INTEGER PRIMARY KEY REFERENCES sales(id) ON DELETE CASCADE,
                factura_id    INTEGER REFERENCES facturas(id) ON DELETE SET NULL,
                remito_id     INTEGER REFERENCES remitos(id) ON DELETE SET NULL,
                turno_id      INTEGER REFERENCES turnos_caja(id) ON DELETE SET NULL,
                mp_order_id   TEXT DEFAULT '',
                mp_payment_id TEXT DEFAULT ''
            )
        """)

        # Seed de módulos: inserta sólo los que no existen aún. La lista de
        # módulos (y el plan que los habilita) es específica de Contalibra —
        # Restolibra tiene su propia lista (con "restaurant" incluido) en su
        # propio init_db().
        _MODULOS_DEFAULT = [
            ("clientes",      1, "basico"),
            ("caja",          1, "basico"),
            ("cajas",         1, "basico"),
            ("ventas",        1, "basico"),
            ("facturacion",   1, "estandar"),
            ("remitos",       1, "estandar"),
            ("presupuestos",  1, "estandar"),
            ("productos",     1, "estandar"),
            ("stock",         1, "premium"),
            ("depositos",     1, "premium"),
            ("reportes",      1, "estandar"),
            ("egresos",           1, "estandar"),
            ("proveedores",       1, "estandar"),
            ("tesoreria",         1, "estandar"),
            ("cuenta_corriente",  1, "estandar"),
            ("listas_precio",     1, "estandar"),
            ("libros_iva",        1, "estandar"),
        ]
        for modulo, habilitado, plan in _MODULOS_DEFAULT:
            conn.execute(
                "INSERT OR IGNORE INTO modulos (modulo, habilitado, plan) VALUES (?,?,?)",
                (modulo, habilitado, plan),
            )
        conn.commit()

    # Backfill de los `parties` espejo de `clients` (libracore v1.2.0). Va
    # al final y FUERA del `with`: necesita que `init_commerce_schema` ya
    # haya creado `parties`, y abre su propia conexión (con la de arriba
    # todavía en transacción daría "database is locked"). Cubre a los
    # clientes creados entre P7 y este fix, que quedaron sin party — sin
    # espejo, venderles falla con FOREIGN KEY constraint (ver
    # libracore/db/clients.py). Idempotente: en una base al día no hace nada.
    sincronizar_parties_de_clientes()


# ── Clients ── movido a db_clients.py, re-exportado arriba ────────────────────


# ── Remitos/Presupuestos ── movido a db_remitos_presupuestos.py, re-exportado arriba ──


# ── Configuración ARCA ── movido a db_arca_config.py, re-exportado arriba ─────


# ── Facturas ── movido a db_facturas.py, re-exportado arriba ──────────────────


# ── Cajas/Caja ── movido a db_caja.py, re-exportado arriba ────────────────────


# ── MercadoPago (pagos/alias/movimientos) ── movido a db_mp.py, re-exportado arriba ──


# ── Dashboard ── movido a db_dashboard.py, re-exportado arriba ────────────────

# ── Usuarios ── movido a db_usuarios.py, re-exportado arriba ──────────────────

# ── Depósitos/Categorías de producto/Productos ── movido a db_productos.py, re-exportado arriba ─

# ── Turnos de caja ── movido a db_turnos.py, re-exportado arriba ──────────────


# ── Stock ── movido a db_stock.py, re-exportado arriba ─────────────────────────


# ── Ventas ── movido a db_ventas.py, re-exportado arriba ──────────────────────


# ── Log de actividad/autenticación ── movido a db_logs.py, re-exportado arriba ─


# ── Módulos ── movido a db_modulos.py, re-exportado arriba ────────────────────

# ── Reportes ── movido a db_reportes.py, re-exportado arriba ──────────────────
# (las 4 funciones de ventas/MP que estaban acá se movieron a db_ventas.py,
# re-exportadas arriba)


# ── Categorías de egreso/Proveedores/Egresos ── movido a db_egresos.py, re-exportado arriba ──


# ── Tesorería ── movido a db_tesoreria.py, re-exportado arriba ────────────────

# ── Cuenta corriente por cliente ── movido a db_cuenta_corriente.py, re-exportado arriba ─


# ── Listas de precios ── movido a db_listas_precio.py, re-exportado arriba ────


# ── Libros IVA ── movido a db_libros_iva.py, re-exportado arriba ──────────────
