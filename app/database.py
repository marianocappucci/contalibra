# Infraestructura compartida y módulos por dominio, extraídos de este archivo
# como parte del split en módulos lógicos (Fase 3 de LibraCore, sub-paso
# previo dentro de cada producto, sin cambiar comportamiento — ver
# wiki/entities/libracore.md). Re-exportados acá para que los call sites
# existentes (`db.get_connection()`, `db.DB_PATH`, `db.create_usuario(...)`,
# etc.) no cambien una línea.
from libracommerce.db.schema import init_schema as init_commerce_schema
from libracore.db.clients import sincronizar_parties_de_clientes
from libracore.db.schema import init_core_schema

from app.db_arca_config import (  # noqa: F401
    actualizar_arca_config,
    crear_arca_config,
    eliminar_arca_config,
    obtener_arca_config,
    obtener_todas_arca_configs,
)
from app.db_caja import (  # noqa: F401
    MEDIOS_PAGO_LABELS,
    anular_caja_movimiento,
    create_caja_config,
    create_caja_movimiento,
    delete_caja_config,
    delete_caja_movimiento,
    get_all_cajas,
    get_caja_config,
    get_caja_movimientos,
    get_caja_resumen,
    get_cobro_factura,
    get_cobros_factura,
    get_default_caja_id,
    set_default_caja,
    update_caja_config,
)
from app.db_clients import (  # noqa: F401
    activar_cliente,
    create_client,
    delete_client,
    desactivar_cliente,
    get_all_clients,
    get_all_clients_including_inactive,
    get_client,
    get_client_by_cuit,
    get_client_by_email,
    get_facturas_by_client,
    tiene_presupuestos_aprobados,
    toggle_auto_facturar,
    update_client,
)
from app.db_core import _AR_TZ, _DATA_DIR, DB_PATH, ES_POSTGRES, _ar_now, get_connection  # noqa: F401
from app.db_cuenta_corriente import (  # noqa: F401
    create_cc_pago,
    delete_cc_pago,
    get_cc_movimientos,
    get_cc_saldo,
    get_clientes_con_saldo_cc,
)
from app.db_dashboard import get_dashboard_data  # noqa: F401
from app.db_egresos import (  # noqa: F401
    create_categoria_egreso,
    create_egreso,
    create_pago_egreso,
    create_proveedor,
    delete_categoria_egreso,
    delete_egreso,
    delete_proveedor,
    get_all_egresos,
    get_all_proveedores,
    get_categorias_egreso,
    get_egreso,
    get_pagos_egreso,
    get_proveedor,
    get_resumen_egresos,
    search_proveedores,
    update_proveedor,
)
from app.db_facturas import (  # noqa: F401
    create_factura,
    delete_factura,
    get_all_facturas,
    get_factura,
    get_factura_por_tipo_pv_nro,
    get_facturas_filtradas,
    get_nc_de_factura,
    get_nd_de_factura,
    get_next_factura_numero,
    get_notas_de_factura,
    search_facturas,
    update_factura_cae,
    update_factura_pdf_path,
)
from app.db_integraciones import (  # noqa: F401
    crear_tablas as crear_tablas_integraciones,
)
from app.db_integraciones import (
    get_alicuota_externa,
    get_origen_de_venta,
    get_usuario_integraciones,
    get_venta_por_referencia,
    registrar_origen,
    set_usuario_integraciones,
)
from app.db_libros_iva import get_egresos_para_iva, get_facturas_para_iva  # noqa: F401
from app.db_listas_precio import (  # noqa: F401
    apply_porcentaje_lista,
    create_lista_precio,
    delete_lista_precio,
    get_all_listas_precio,
    get_lista_precio,
    get_lista_precio_items,
    get_precio_en_lista,
    get_precios_lista_dict,
    importar_precios_lista,
    save_lista_precio_items,
    update_lista_precio,
)
from app.db_logs import (  # noqa: F401
    contar_login_fallidos_recientes,
    get_actividad_count,
    get_actividad_log,
    get_auth_log,
    registrar_auth_event,
)
from app.db_modulos import apply_plan, get_modulos  # noqa: F401
from app.db_mp import (  # noqa: F401
    crear_alias_facturacion,
    create_mp_movimiento,
    create_mp_pago,
    eliminar_alias_facturacion,
    get_alias_facturacion_by_cliente,
    get_cliente_por_alias_pago,
    get_mp_movimiento_by_id,
    get_mp_movimiento_by_mp_id,
    get_mp_movimientos_by_estado,
    get_mp_movimientos_historial,
    get_mp_pago,
    get_mp_pago_by_id,
    get_mp_pagos_by_estado,
    get_mp_pagos_historial,
    get_mp_pending_count,
    resolver_cliente_pago,
    update_mp_movimiento_datos,
    update_mp_movimiento_estado,
    update_mp_pago_estado,
    vincular_mp_pago_cliente,
)
from app.db_productos import (  # noqa: F401
    create_categoria_producto,
    create_deposito,
    create_producto,
    delete_categoria_producto,
    delete_deposito,
    delete_producto,
    get_all_depositos,
    get_all_productos,
    get_categorias_producto,
    get_default_deposito_id,
    get_deposito,
    get_producto,
    get_producto_by_codigo,
    get_stock_por_deposito,
    get_stock_producto_todos_depositos,
    set_default_deposito,
    transferir_stock,
    update_deposito,
    update_producto,
)
from app.db_recibos import (  # noqa: F401
    anular_recibo,
    contar_recibos,
    emitir_recibo_cobranza,
    emitir_recibo_factura,
    emitir_recibo_venta,
    get_recibo,
    get_recibos,
)
from app.db_remitos_presupuestos import (  # noqa: F401
    auto_vencimiento_presupuestos,
    create_presupuesto,
    create_remito,
    delete_presupuesto,
    delete_remito,
    get_all_presupuestos,
    get_all_remitos,
    get_next_presupuesto_number,
    get_next_remito_number,
    get_presupuesto,
    get_presupuestos_by_client,
    get_presupuestos_count_by_estado,
    get_remito,
    get_remitos_by_client,
    search_presupuestos,
    search_remitos,
    update_presupuesto,
    update_presupuesto_pdf_path,
    update_presupuesto_remito_id,
    update_presupuesto_status,
    update_remito,
    update_remito_pdf_path,
)
from app.db_reportes import (  # noqa: F401
    get_reporte_caja,
    get_reporte_caja_medios,
    get_reporte_medios_pago,
    get_reporte_productos_top,
    get_reporte_resumen,
    get_reporte_stock_bajo,
    get_reporte_ventas,
)
from app.db_stock import (  # noqa: F401
    add_movimiento_stock,
    ajustar_stock,
    descontar_stock_venta,
    get_movimientos_stock,
    get_stock_actual,
    get_stock_todos,
)
from app.db_tesoreria import (  # noqa: F401
    create_cuenta_tesoreria,
    create_movimiento_tesoreria,
    create_transferencia_tesoreria,
    delete_cuenta_tesoreria,
    delete_movimiento_tesoreria,
    get_all_cuentas_tesoreria,
    get_cuenta_tesoreria,
    get_movimientos_tesoreria,
    get_resumen_tesoreria,
    update_cuenta_tesoreria,
)
from app.db_turnos import (  # noqa: F401
    cerrar_turno,
    create_turno,
    get_all_turnos,
    get_resumen_turno,
    get_turno,
    get_turno_activo,
    get_turno_activo_any,
    vincular_venta_turno,
)
from app.db_usuarios import (  # noqa: F401
    _DUMMY_PASSWORD_HASH,
    SIN_CAMBIOS,
    ClaveDeCifradoAusente,
    EmailNotConfigured,
    InvalidResetToken,
    _hash_password,
    _verify_password,
    borrar_config_smtp,
    check_usuario_credentials,
    create_usuario,
    delete_usuario,
    ensure_admin_user,
    ensure_demo_user,
    get_all_usuarios,
    get_usuario_by_id,
    get_usuario_by_username,
    guardar_config_smtp,
    # Config SMTP por backoffice, cifrada en reposo (libraauth v0.6.0).
    leer_config_smtp,
    resetear_password_con_token,
    # Recuperacion de contrasena por correo (libraauth v0.5.0).
    solicitar_reset_password,
    update_usuario,
    update_usuario_password,
)
from app.db_ventas import (  # noqa: F401
    acreditar_pago_qr,
    add_venta_pago,
    add_venta_pago_referencia_mp,
    anular_venta,
    crear_venta_directa,
    create_venta,
    get_all_ventas,
    get_next_venta_numero,
    get_venta,
    get_venta_by_mp_order,
    set_venta_mp_order,
    set_venta_mp_payment,
    vincular_cobros_de_venta,
    vincular_venta_factura,
    vincular_venta_remito,
)
from app.schema_propio import init_schema_propio  # noqa: F401  (lo usa init_db)


def _repuntar_fk_ventas_pagos_postgres(conn):
    """Lo mismo que el rebuild de SQLite, pero en dos `ALTER TABLE`.

    PostgreSQL sí sabe cambiar una constraint, así que no hay que reconstruir
    la tabla ni copiar filas: se busca la FK actual de `venta_id`, y si no
    apunta ya a `sales` se la reemplaza. Sin `PRAGMA`, sin `sqlite_master` y
    sin mover un solo dato.
    """
    definiciones = conn.execute("""
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conrelid = 'ventas_pagos'::regclass AND contype = 'f'
    """).fetchall()

    if any("REFERENCES sales(" in d[1] for d in definiciones):
        return

    huerfanas = _avisar_pagos_huerfanos(conn)

    for nombre, definicion in definiciones:
        if "venta_id" in definicion:
            conn.execute(f"ALTER TABLE ventas_pagos DROP CONSTRAINT {nombre}")

    # 🔴 `NOT VALID` cuando hay filas colgadas, y es el equivalente EXACTO de lo
    # que hace el camino de SQLite.
    #
    # Allá el rebuild copia las filas con el pragma apagado: las huérfanas
    # sobreviven y la FK queda declarada pero sin verificar sobre ellas. Es
    # deliberado — son registros de dinero, y descartarlos tiene que ser
    # decisión de una persona y no efecto de un deploy.
    #
    # PostgreSQL **no acepta** agregar una FK que las filas existentes violan.
    # `NOT VALID` dice exactamente lo mismo: no revises lo que ya está, aplicá
    # la regla de acá en adelante. Sin esto las únicas salidas serían tumbar el
    # arranque o borrar las filas, y las dos son peores.
    #
    # Se termina de validar a mano, con `ALTER TABLE ventas_pagos VALIDATE
    # CONSTRAINT ventas_pagos_venta_id_fkey`, cuando alguien resolvió esas filas.
    sufijo = " NOT VALID" if huerfanas else ""
    conn.execute(
        "ALTER TABLE ventas_pagos ADD CONSTRAINT ventas_pagos_venta_id_fkey "
        f"FOREIGN KEY (venta_id) REFERENCES sales(id) ON DELETE CASCADE{sufijo}"
    )
    conn.commit()


def _avisar_pagos_huerfanos(conn):
    """Filas que no tienen su venta en `sales`.

    NO se descartan: son registros de dinero. Se avisa y se siguen, porque
    quedan referenciando una venta inexistente y eso tiene que ser una decisión
    de alguien, no un efecto silencioso de un deploy.
    """
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
    return huerfanas


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

    Contra **PostgreSQL** esto no es un rebuild: la FK se cambia con dos
    `ALTER TABLE`, y allá no existen ni `sqlite_master` ni el `PRAGMA`. Los dos
    caminos hacen lo mismo y quedan separados a propósito — disimular la
    diferencia sería peor, porque el rebuild de 12 pasos existe **precisamente**
    porque SQLite no sabe cambiar una constraint.
    """
    if ES_POSTGRES:
        _repuntar_fk_ventas_pagos_postgres(conn)
        return

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
                created_at TEXT DEFAULT (datetime('now','-3 hours'))
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

        # Las 3 tablas propias de este producto —`venta_links`,
        # `integraciones_config` y `ventas_origen_externo`—. El DDL vive en
        # `app/schema_propio.py` y no acá desde el 2026-08-25, porque la
        # baseline de Alembic (`migrations/versions/0001_baseline_contalibra.py`)
        # llama a esa MISMA función: si el DDL siguiera suelto acá, la revisión
        # tendría que re-expresarlo y serían dos fuentes de verdad que se
        # desincronizan en el primer cambio.
        #
        # 🔴 Desde esa revisión la función es de **sólo lectura**: una columna
        # nueva va como revisión de Alembic, no como línea agregada ahí. Ver su
        # docstring para el reparto completo de las 61 tablas.
        init_schema_propio(conn)

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
            # Add-on opcional (paquete mayorista): NO pertenece a ningún plan.
            # Arranca apagado y se habilita por instancia desde el backoffice.
            # `plan="addon"` y no NULL porque la columna es NOT NULL; el valor es
            # sólo bookkeeping (nadie lo lee para decidir gateo). `apply_plan` y
            # `aplicar_plan_en_db` lo saltean vía `plans.ADDONS`, así que sobrevive
            # a los cambios de plan.
            ("mayorista",         0, "addon"),
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
