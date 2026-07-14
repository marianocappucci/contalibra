import sqlite3
import json
import os
import contextlib
from datetime import datetime as _datetime, timezone as _timezone, timedelta as _timedelta

# Infraestructura compartida y módulos por dominio, extraídos de este archivo
# como parte del split en módulos lógicos (Fase 3 de LibraCore, sub-paso
# previo dentro de cada producto, sin cambiar comportamiento — ver
# wiki/entities/libracore.md). Re-exportados acá para que los call sites
# existentes (`db.get_connection()`, `db.DB_PATH`, `db.create_usuario(...)`,
# etc.) no cambien una línea.
from db_core import _AR_TZ, _ar_now, _DATA_DIR, DB_PATH, get_connection  # noqa: F401
from db_usuarios import (  # noqa: F401
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
)
from db_tesoreria import (  # noqa: F401
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
from db_caja import (  # noqa: F401
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
from db_egresos import (  # noqa: F401
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
from db_modulos import get_modulos, apply_plan  # noqa: F401
from db_listas_precio import (  # noqa: F401
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
from db_turnos import (  # noqa: F401
    create_turno,
    get_turno_activo,
    get_turno_activo_any,
    get_all_turnos,
    get_turno,
    get_resumen_turno,
    cerrar_turno,
    vincular_venta_turno,
)
from db_dashboard import get_dashboard_data  # noqa: F401
from db_logs import (  # noqa: F401
    get_actividad_log,
    get_actividad_count,
    registrar_auth_event,
    get_auth_log,
    contar_login_fallidos_recientes,
)
from db_arca_config import (  # noqa: F401
    crear_arca_config,
    obtener_arca_config,
    obtener_todas_arca_configs,
    actualizar_arca_config,
    eliminar_arca_config,
)
from db_cuenta_corriente import (  # noqa: F401
    get_cc_saldo,
    get_cc_movimientos,
    get_clientes_con_saldo_cc,
    create_cc_pago,
    delete_cc_pago,
)
from db_libros_iva import get_facturas_para_iva, get_egresos_para_iva  # noqa: F401
from db_reportes import (  # noqa: F401
    get_reporte_ventas,
    get_reporte_medios_pago,
    get_reporte_productos_top,
    get_reporte_caja,
    get_reporte_caja_medios,
    get_reporte_stock_bajo,
    get_reporte_resumen,
)
from db_productos import (  # noqa: F401
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


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                address       TEXT,
                cuit_dni      TEXT,
                email         TEXT,
                phone         TEXT,
                iva_condition TEXT DEFAULT '',
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS remitos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                number         TEXT NOT NULL UNIQUE,
                date           TEXT NOT NULL,
                client_id      INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                client_name    TEXT NOT NULL,
                client_address TEXT,
                client_cuit    TEXT,
                client_email   TEXT,
                client_phone   TEXT,
                items          TEXT NOT NULL,
                subtotal       REAL NOT NULL,
                tax_rate       REAL NOT NULL DEFAULT 0.21,
                tax_amount     REAL NOT NULL,
                total          REAL NOT NULL,
                observations   TEXT,
                pdf_path       TEXT,
                created_at     TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS presupuestos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                number          TEXT NOT NULL UNIQUE,
                date            TEXT NOT NULL,
                valid_until     TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'pendiente',
                client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                client_name     TEXT NOT NULL,
                client_address  TEXT,
                client_cuit     TEXT,
                client_email    TEXT,
                client_phone    TEXT,
                items           TEXT NOT NULL,
                subtotal        REAL NOT NULL,
                tax_rate        REAL NOT NULL DEFAULT 0.21,
                tax_amount      REAL NOT NULL,
                total           REAL NOT NULL,
                observations    TEXT,
                pdf_path        TEXT,
                remito_id       INTEGER REFERENCES remitos(id),
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS facturas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo            INTEGER NOT NULL,
                punto_venta     INTEGER NOT NULL,
                numero          INTEGER NOT NULL,
                fecha           TEXT NOT NULL,
                cliente_cuit    TEXT,
                cliente_razon   TEXT,
                cliente_iva_cond INTEGER,
                items           TEXT NOT NULL,
                subtotal        REAL NOT NULL,
                iva_amount      REAL NOT NULL,
                total           REAL NOT NULL,
                concepto        INTEGER NOT NULL DEFAULT 1,
                cae             TEXT,
                cae_vto         TEXT,
                observaciones   TEXT,
                pdf_path        TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS cajas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre      TEXT NOT NULL,
                descripcion TEXT DEFAULT '',
                medios_pago TEXT NOT NULL DEFAULT '[]',
                activo      INTEGER NOT NULL DEFAULT 1,
                es_default  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS caja_movimientos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT NOT NULL,
                tipo        TEXT NOT NULL,
                concepto    TEXT NOT NULL,
                monto       REAL NOT NULL,
                referencia  TEXT DEFAULT '',
                factura_id  INTEGER,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS mp_pagos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                mp_payment_id   TEXT NOT NULL UNIQUE,
                status          TEXT,
                monto           REAL,
                payer_email     TEXT,
                payer_name      TEXT,
                factura_id      INTEGER,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS mp_movimientos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                mp_movement_id  TEXT NOT NULL UNIQUE,
                tipo            TEXT,
                monto           REAL,
                fecha           TEXT,
                descripcion     TEXT,
                origen_nombre   TEXT,
                origen_banco    TEXT,
                origen_cbu      TEXT,
                payer_email     TEXT,
                payer_name      TEXT,
                payer_id_type   TEXT,
                payer_id_number TEXT,
                estado_factura  TEXT DEFAULT 'pendiente',
                factura_id      INTEGER,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS facturacion_alias (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo        TEXT NOT NULL CHECK (tipo IN ('cuit', 'email')),
                valor       TEXT NOT NULL,
                cliente_id  INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                activo      INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now')),
                UNIQUE (tipo, valor)
            );

            CREATE TABLE IF NOT EXISTS arca_config (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa         TEXT NOT NULL UNIQUE,
                cuit            TEXT NOT NULL,
                punto_venta     INTEGER NOT NULL,
                clave_path      TEXT NOT NULL,
                certificado_path TEXT NOT NULL,
                ambiente        TEXT DEFAULT 'homologacion',
                activo          INTEGER DEFAULT 1,
                alias           TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                nombre        TEXT NOT NULL,
                email         TEXT DEFAULT '',
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'operador',
                activo        INTEGER NOT NULL DEFAULT 1,
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS modulos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                modulo     TEXT NOT NULL UNIQUE,
                habilitado INTEGER NOT NULL DEFAULT 1,
                plan       TEXT NOT NULL DEFAULT 'estandar'
            );

            CREATE TABLE IF NOT EXISTS productos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo       TEXT UNIQUE,
                nombre       TEXT NOT NULL,
                descripcion  TEXT DEFAULT '',
                precio_venta REAL NOT NULL DEFAULT 0,
                precio_costo REAL NOT NULL DEFAULT 0,
                unidad       TEXT NOT NULL DEFAULT 'u',
                categoria    TEXT DEFAULT '',
                activo       INTEGER NOT NULL DEFAULT 1,
                created_at   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS depositos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre      TEXT NOT NULL,
                descripcion TEXT DEFAULT '',
                activo      INTEGER NOT NULL DEFAULT 1,
                es_default  INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS categorias_producto (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS categorias_egreso (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS proveedores (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre        TEXT NOT NULL,
                cuit_dni      TEXT DEFAULT '',
                email         TEXT DEFAULT '',
                phone         TEXT DEFAULT '',
                address       TEXT DEFAULT '',
                iva_condition TEXT DEFAULT '',
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS egresos (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha            TEXT NOT NULL,
                proveedor_id     INTEGER REFERENCES proveedores(id) ON DELETE SET NULL,
                proveedor_nombre TEXT NOT NULL DEFAULT '',
                tipo_comprobante TEXT NOT NULL DEFAULT 'otro',
                numero           TEXT DEFAULT '',
                categoria        TEXT DEFAULT '',
                concepto         TEXT NOT NULL,
                monto_neto       REAL NOT NULL DEFAULT 0,
                iva_pct          REAL NOT NULL DEFAULT 0,
                iva_monto        REAL NOT NULL DEFAULT 0,
                total            REAL NOT NULL,
                estado           TEXT NOT NULL DEFAULT 'pendiente',
                observaciones    TEXT DEFAULT '',
                usuario_id       INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                created_at       TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS egresos_pagos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                egreso_id   INTEGER NOT NULL REFERENCES egresos(id) ON DELETE CASCADE,
                fecha       TEXT NOT NULL,
                monto       REAL NOT NULL,
                caja_id     INTEGER REFERENCES cajas(id) ON DELETE SET NULL,
                medio_pago  TEXT DEFAULT '',
                referencia  TEXT DEFAULT '',
                usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS turnos_caja (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id             INTEGER NOT NULL REFERENCES usuarios(id),
                apertura               TEXT NOT NULL,
                cierre                 TEXT,
                monto_inicial          REAL NOT NULL DEFAULT 0,
                monto_declarado_cierre REAL,
                monto_esperado_cierre  REAL,
                estado                 TEXT NOT NULL DEFAULT 'abierto',
                notas                  TEXT DEFAULT '',
                created_at             TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS movimientos_stock (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                tipo        TEXT NOT NULL,
                cantidad    REAL NOT NULL,
                referencia  TEXT DEFAULT '',
                venta_id    INTEGER REFERENCES ventas(id) ON DELETE SET NULL,
                usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                fecha       TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ventas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                numero          TEXT NOT NULL UNIQUE,
                fecha           TEXT NOT NULL,
                cliente_id      INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                cliente_nombre  TEXT DEFAULT '',
                items           TEXT NOT NULL,
                subtotal        REAL NOT NULL DEFAULT 0,
                descuento       REAL NOT NULL DEFAULT 0,
                total           REAL NOT NULL DEFAULT 0,
                estado          TEXT NOT NULL DEFAULT 'cobrada',
                factura_id      INTEGER REFERENCES facturas(id) ON DELETE SET NULL,
                remito_id       INTEGER REFERENCES remitos(id) ON DELETE SET NULL,
                usuario_id      INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                observaciones   TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ventas_pagos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id   INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
                medio      TEXT NOT NULL,
                monto      REAL NOT NULL,
                referencia TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        # Migración: columnas faltantes
        cols = [r[1] for r in conn.execute("PRAGMA table_info(clients)").fetchall()]
        if "iva_condition" not in cols:
            conn.execute("ALTER TABLE clients ADD COLUMN iva_condition TEXT DEFAULT ''")
        if "activo" not in cols:
            conn.execute("ALTER TABLE clients ADD COLUMN activo INTEGER DEFAULT 1")
        fact_cols = [r[1] for r in conn.execute("PRAGMA table_info(facturas)").fetchall()]
        if "cliente_domicilio" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN cliente_domicilio TEXT DEFAULT ''")
        if "fch_serv_desde" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN fch_serv_desde TEXT DEFAULT ''")
        if "fch_serv_hasta" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN fch_serv_hasta TEXT DEFAULT ''")
        if "fch_vto_pago" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN fch_vto_pago TEXT DEFAULT ''")
        if "cbte_asoc_tipo" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN cbte_asoc_tipo INTEGER DEFAULT 0")
        if "cbte_asoc_pv" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN cbte_asoc_pv INTEGER DEFAULT 0")
        if "cbte_asoc_nro" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN cbte_asoc_nro INTEGER DEFAULT 0")
        if "condicion_venta" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN condicion_venta TEXT DEFAULT ''")
        if "usuario_id" not in fact_cols:
            conn.execute("ALTER TABLE facturas ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL")

        remito_cols = [r[1] for r in conn.execute("PRAGMA table_info(remitos)").fetchall()]
        if remito_cols and "usuario_id" not in remito_cols:
            conn.execute("ALTER TABLE remitos ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL")

        pres_cols = [r[1] for r in conn.execute("PRAGMA table_info(presupuestos)").fetchall()]
        if pres_cols and "usuario_id" not in pres_cols:
            conn.execute("ALTER TABLE presupuestos ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL")

        caja_cols = [r[1] for r in conn.execute("PRAGMA table_info(caja_movimientos)").fetchall()]
        if caja_cols and "usuario_id" not in caja_cols:
            conn.execute("ALTER TABLE caja_movimientos ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL")

        prod_cols = [r[1] for r in conn.execute("PRAGMA table_info(productos)").fetchall()]
        if "stock_minimo" not in prod_cols:
            conn.execute("ALTER TABLE productos ADD COLUMN stock_minimo REAL NOT NULL DEFAULT 0")
        ventas_cols = [r[1] for r in conn.execute("PRAGMA table_info(ventas)").fetchall()]
        if ventas_cols and "turno_id" not in ventas_cols:
            conn.execute("ALTER TABLE ventas ADD COLUMN turno_id INTEGER REFERENCES turnos_caja(id) ON DELETE SET NULL")
        if ventas_cols and "mp_order_id" not in ventas_cols:
            conn.execute("ALTER TABLE ventas ADD COLUMN mp_order_id TEXT DEFAULT ''")
        if ventas_cols and "mp_payment_id" not in ventas_cols:
            conn.execute("ALTER TABLE ventas ADD COLUMN mp_payment_id TEXT DEFAULT ''")

        client_cols = [r[1] for r in conn.execute("PRAGMA table_info(clients)").fetchall()]
        if "auto_facturar" not in client_cols:
            conn.execute("ALTER TABLE clients ADD COLUMN auto_facturar INTEGER NOT NULL DEFAULT 0")

        mp_cols = [r[1] for r in conn.execute("PRAGMA table_info(mp_pagos)").fetchall()]
        if mp_cols and "estado_factura" not in mp_cols:
            conn.execute("ALTER TABLE mp_pagos ADD COLUMN estado_factura TEXT DEFAULT NULL")
        if mp_cols and "payment_type" not in mp_cols:
            conn.execute("ALTER TABLE mp_pagos ADD COLUMN payment_type TEXT DEFAULT NULL")
        if mp_cols and "payment_method" not in mp_cols:
            conn.execute("ALTER TABLE mp_pagos ADD COLUMN payment_method TEXT DEFAULT NULL")
        if mp_cols and "descripcion_mp" not in mp_cols:
            conn.execute("ALTER TABLE mp_pagos ADD COLUMN descripcion_mp TEXT DEFAULT NULL")
        if mp_cols and "payer_id_type" not in mp_cols:
            conn.execute("ALTER TABLE mp_pagos ADD COLUMN payer_id_type TEXT DEFAULT NULL")
        if mp_cols and "payer_id_number" not in mp_cols:
            conn.execute("ALTER TABLE mp_pagos ADD COLUMN payer_id_number TEXT DEFAULT NULL")

        # Migración: cajas — caja principal por defecto
        if conn.execute("SELECT COUNT(*) FROM cajas").fetchone()[0] == 0:
            _todos_medios = json.dumps([
                "efectivo", "transferencia", "mercadopago",
                "cuenta_dni", "billetera", "cuenta_corriente",
            ])
            cur = conn.execute(
                "INSERT INTO cajas (nombre, descripcion, medios_pago, es_default) VALUES (?,?,?,1)",
                ("Caja Principal", "Caja por defecto del sistema", _todos_medios),
            )
            _default_caja_id = cur.lastrowid
        else:
            _default_caja_id = conn.execute(
                "SELECT id FROM cajas WHERE es_default=1 LIMIT 1"
            ).fetchone()
            _default_caja_id = _default_caja_id[0] if _default_caja_id else conn.execute(
                "SELECT id FROM cajas ORDER BY id LIMIT 1"
            ).fetchone()[0]

        cm_cols = [r[1] for r in conn.execute("PRAGMA table_info(caja_movimientos)").fetchall()]
        if cm_cols and "caja_id" not in cm_cols:
            conn.execute("ALTER TABLE caja_movimientos ADD COLUMN caja_id INTEGER REFERENCES cajas(id) ON DELETE SET NULL")
            conn.execute("UPDATE caja_movimientos SET caja_id=? WHERE caja_id IS NULL", (_default_caja_id,))
        if cm_cols and "medio_pago" not in cm_cols:
            conn.execute("ALTER TABLE caja_movimientos ADD COLUMN medio_pago TEXT DEFAULT ''")

        tc_cols = [r[1] for r in conn.execute("PRAGMA table_info(turnos_caja)").fetchall()]
        if tc_cols and "caja_id" not in tc_cols:
            conn.execute("ALTER TABLE turnos_caja ADD COLUMN caja_id INTEGER REFERENCES cajas(id) ON DELETE SET NULL")
            conn.execute("UPDATE turnos_caja SET caja_id=? WHERE caja_id IS NULL", (_default_caja_id,))

        # Migración: deposito_id en movimientos_stock
        ms_cols = [r[1] for r in conn.execute("PRAGMA table_info(movimientos_stock)").fetchall()]
        if ms_cols and "deposito_id" not in ms_cols:
            conn.execute("ALTER TABLE movimientos_stock ADD COLUMN deposito_id INTEGER REFERENCES depositos(id) ON DELETE SET NULL")

        # Depósito principal por defecto (se crea solo si no existe ninguno)
        if conn.execute("SELECT COUNT(*) FROM depositos").fetchone()[0] == 0:
            cur = conn.execute(
                "INSERT INTO depositos (nombre, descripcion, es_default) VALUES (?,?,1)",
                ("Depósito Principal", "Depósito por defecto del sistema"),
            )
            default_id = cur.lastrowid
            # Asignar movimientos existentes sin depósito al depósito default
            conn.execute(
                "UPDATE movimientos_stock SET deposito_id=? WHERE deposito_id IS NULL",
                (default_id,),
            )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS cuentas_tesoreria (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre        TEXT NOT NULL,
                tipo          TEXT NOT NULL DEFAULT 'banco',
                banco         TEXT DEFAULT '',
                numero        TEXT DEFAULT '',
                descripcion   TEXT DEFAULT '',
                saldo_inicial REAL NOT NULL DEFAULT 0,
                activa        INTEGER NOT NULL DEFAULT 1,
                orden         INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS movimientos_tesoreria (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha             TEXT NOT NULL,
                cuenta_id         INTEGER NOT NULL REFERENCES cuentas_tesoreria(id) ON DELETE CASCADE,
                tipo              TEXT NOT NULL,
                monto             REAL NOT NULL,
                concepto          TEXT NOT NULL DEFAULT '',
                referencia        TEXT DEFAULT '',
                cuenta_destino_id INTEGER REFERENCES cuentas_tesoreria(id) ON DELETE SET NULL,
                transferencia_id  INTEGER,
                usuario_id        INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                created_at        TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                evento     TEXT NOT NULL,
                username   TEXT NOT NULL,
                ip         TEXT,
                detalle    TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS listas_precio (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre      TEXT NOT NULL,
                descripcion TEXT DEFAULT '',
                es_default  INTEGER NOT NULL DEFAULT 0,
                activa      INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS lista_precio_items (
                lista_id    INTEGER NOT NULL REFERENCES listas_precio(id) ON DELETE CASCADE,
                producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                precio      REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (lista_id, producto_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS cc_pagos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id  INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
                monto       REAL NOT NULL,
                fecha       TEXT NOT NULL,
                concepto    TEXT DEFAULT '',
                referencia  TEXT DEFAULT '',
                medio_pago  TEXT DEFAULT 'efectivo',
                caja_id     INTEGER REFERENCES cajas(id) ON DELETE SET NULL,
                usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.executescript("""
            -- Índices mínimos sobre las tablas de mayor tráfico (reportes,
            -- filtros por fecha/cliente) — el esquema no tenía ninguno
            -- (hallazgo cruzado desde la auditoría de Restolibra, ver
            -- wiki/analyses/restolibra-auditoria-produccion).
            CREATE INDEX IF NOT EXISTS idx_clients_cuit_norm ON clients(REPLACE(cuit_dni, '-', ''));
            CREATE INDEX IF NOT EXISTS idx_facturas_fecha ON facturas(fecha);
            CREATE INDEX IF NOT EXISTS idx_facturas_cliente_cuit ON facturas(cliente_cuit);
            CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha);
            CREATE INDEX IF NOT EXISTS idx_caja_movimientos_fecha ON caja_movimientos(fecha);
            CREATE INDEX IF NOT EXISTS idx_cc_pagos_cliente ON cc_pagos(cliente_id);
            CREATE INDEX IF NOT EXISTS idx_movimientos_stock_producto ON movimientos_stock(producto_id);
        """)

        # UNIQUE aparte (no en el executescript de arriba): si por algún motivo
        # ya existieran duplicados de tipo+punto_venta+numero en una instancia
        # (no debería, pero es defensivo), que falle solo esto sin tumbar el
        # resto de init_db al arrancar la app. Cierra la race condition de
        # numeración (hallazgo cruzado desde la auditoría de Restolibra) junto
        # con el retry en create_factura().
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_facturas_numero_unico "
                "ON facturas(tipo, punto_venta, numero)"
            )
        except sqlite3.Error as e:
            print(f"[WARN] No se pudo crear idx_facturas_numero_unico (¿hay duplicados "
                  f"de tipo+punto_venta+numero?): {e}")

        # Seed de módulos: inserta sólo los que no existen aún
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

        _CATEGORIAS_EGRESO_DEFAULT = [
            "Mercadería / Materias primas",
            "Alquiler",
            "Servicios (luz, gas, internet)",
            "Sueldos y honorarios",
            "Impuestos y tasas",
            "Transporte y logística",
            "Mantenimiento y reparaciones",
            "Publicidad y marketing",
            "Bancarios y financieros",
            "Otros",
        ]
        for cat in _CATEGORIAS_EGRESO_DEFAULT:
            conn.execute("INSERT OR IGNORE INTO categorias_egreso (nombre) VALUES (?)", (cat,))


# ── Clients ────────────────────────────────────────────────────────────────────

def create_client(name, address="", cuit_dni="", email="", phone="", iva_condition=""):
    if (cuit_dni or "").replace("-", "").strip():
        existing = get_client_by_cuit(cuit_dni)
        if existing:
            estado = "activo" if existing.get("activo") else "inactivo"
            sugerencia = "Reactivalo desde /clientes en vez de crear uno nuevo." if not existing.get("activo") \
                else "Editalo si necesitás cambiar sus datos."
            raise ValueError(
                f'Ya existe un cliente con el CUIT/DNI {cuit_dni}: "{existing["name"]}" ({estado}). {sugerencia}'
            )
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO clients (name, address, cuit_dni, email, phone, iva_condition) VALUES (?,?,?,?,?,?)",
            (name, address, cuit_dni, email, phone, iva_condition),
        )
        return cur.lastrowid


def get_all_clients():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM clients WHERE activo = 1 ORDER BY name")]


def get_all_clients_including_inactive():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM clients ORDER BY name")]


def get_client(client_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        return dict(row) if row else None


def desactivar_cliente(client_id: int) -> bool:
    """Marca un cliente como inactivo (soft delete)."""
    with get_connection() as conn:
        conn.execute("UPDATE clients SET activo = 0 WHERE id = ?", (client_id,))
        return True


def activar_cliente(client_id: int) -> bool:
    """Reactiva un cliente previamente desactivado."""
    with get_connection() as conn:
        conn.execute("UPDATE clients SET activo = 1 WHERE id = ?", (client_id,))
        return True


def tiene_presupuestos_aprobados(client_id: int) -> bool:
    """Verifica si un cliente tiene presupuestos en estado 'aceptado'."""
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM presupuestos WHERE client_id = ? AND status = 'aceptado'",
            (client_id,)
        ).fetchone()
        return result[0] > 0 if result else False


def get_facturas_by_client(cuit_dni: str, name: str, limit: int = 100) -> list:
    """Facturas asociadas a un cliente, buscando por CUIT o razón social."""
    with get_connection() as conn:
        conds, params = [], []
        if cuit_dni:
            conds.append("cliente_cuit = ?")
            params.append(cuit_dni)
        if name:
            conds.append("cliente_razon = ?")
            params.append(name)
        if not conds:
            return []
        where = " OR ".join(conds)
        rows = conn.execute(
            f"SELECT * FROM facturas WHERE {where} ORDER BY id DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def update_client(client_id, name=None, address=None, cuit_dni=None, email=None,
                  phone=None, iva_condition=None, auto_facturar=None):
    client = get_client(client_id)
    if not client:
        return
    with get_connection() as conn:
        conn.execute(
            """UPDATE clients SET name=?, address=?, cuit_dni=?, email=?, phone=?,
               iva_condition=?, auto_facturar=? WHERE id=?""",
            (
                name          if name          is not None else client["name"],
                address       if address       is not None else client["address"],
                cuit_dni      if cuit_dni      is not None else client["cuit_dni"],
                email         if email         is not None else client["email"],
                phone         if phone         is not None else client["phone"],
                iva_condition if iva_condition is not None else client.get("iva_condition", ""),
                int(auto_facturar) if auto_facturar is not None else int(client.get("auto_facturar", 0)),
                client_id,
            ),
        )


def toggle_auto_facturar(client_id: int) -> bool:
    """Invierte el flag auto_facturar. Devuelve el nuevo valor."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE clients SET auto_facturar = 1 - auto_facturar WHERE id=?",
            (client_id,),
        )
        row = conn.execute("SELECT auto_facturar FROM clients WHERE id=?", (client_id,)).fetchone()
        return bool(row["auto_facturar"]) if row else False


def delete_client(client_id):
    with get_connection() as conn:
        remito_count = conn.execute(
            "SELECT COUNT(*) FROM remitos WHERE client_id=?", (client_id,)
        ).fetchone()[0]
        presupuesto_count = conn.execute(
            "SELECT COUNT(*) FROM presupuestos WHERE client_id=?", (client_id,)
        ).fetchone()[0]
        total_count = remito_count + presupuesto_count
        if total_count > 0:
            msg_parts = []
            if remito_count > 0:
                msg_parts.append(f"{remito_count} remito(s)")
            if presupuesto_count > 0:
                msg_parts.append(f"{presupuesto_count} presupuesto(s)")
            raise ValueError(f"El cliente tiene {' y '.join(msg_parts)} asociado(s) y no puede eliminarse.")
        conn.execute("DELETE FROM clients WHERE id=?", (client_id,))


# ── Remitos ────────────────────────────────────────────────────────────────────

def get_next_remito_number():
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(id) FROM remitos").fetchone()
        next_id = (row[0] or 0) + 1
        return f"0001-{next_id:08d}"


def create_remito(number, date, client_id, client_name, client_address, client_cuit,
                  client_email, client_phone, items, subtotal, tax_rate, tax_amount,
                  total, observations="", pdf_path="", usuario_id=None):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO remitos
               (number, date, client_id, client_name, client_address, client_cuit,
                client_email, client_phone, items, subtotal, tax_rate, tax_amount,
                total, observations, pdf_path, usuario_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                number, date, client_id, client_name, client_address, client_cuit,
                client_email, client_phone, json.dumps(items, ensure_ascii=False),
                subtotal, tax_rate, tax_amount, total, observations, pdf_path, usuario_id,
            ),
        )
        return cur.lastrowid


def update_remito_pdf_path(remito_id, pdf_path):
    with get_connection() as conn:
        conn.execute("UPDATE remitos SET pdf_path=? WHERE id=?", (pdf_path, remito_id))


def get_all_remitos(limit=100):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM remitos ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def get_remito(remito_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM remitos WHERE id=?", (remito_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        return d


def get_remitos_by_client(client_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM remitos WHERE client_id=? ORDER BY id DESC", (client_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def search_remitos(query):
    q = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM remitos
               WHERE number LIKE ? OR client_name LIKE ? OR observations LIKE ?
               ORDER BY id DESC""",
            (q, q, q),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


# ── Presupuestos ───────────────────────────────────────────────────────────────

def get_next_presupuesto_number():
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(id) FROM presupuestos").fetchone()
        next_id = (row[0] or 0) + 1
        return f"PRES-{next_id:08d}"


def auto_vencimiento_presupuestos():
    """Marca como 'vencido' los presupuestos enviados cuya validez expiró."""
    with get_connection() as conn:
        conn.execute(
            """UPDATE presupuestos SET status='vencido'
               WHERE status IN ('enviado', 'pendiente')
               AND valid_until < date('now')"""
        )


def create_presupuesto(number, date, valid_until, client_id, client_name, client_address,
                       client_cuit, client_email, client_phone, items, subtotal, tax_rate,
                       tax_amount, total, observations="", pdf_path="", status="borrador",
                       usuario_id=None):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO presupuestos
               (number, date, valid_until, status, client_id, client_name, client_address,
                client_cuit, client_email, client_phone, items, subtotal, tax_rate,
                tax_amount, total, observations, pdf_path, usuario_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                number, date, valid_until, status, client_id, client_name, client_address,
                client_cuit, client_email, client_phone, json.dumps(items, ensure_ascii=False),
                subtotal, tax_rate, tax_amount, total, observations, pdf_path, usuario_id,
            ),
        )
        return cur.lastrowid


def update_presupuesto_pdf_path(presupuesto_id, pdf_path):
    with get_connection() as conn:
        conn.execute("UPDATE presupuestos SET pdf_path=? WHERE id=?", (pdf_path, presupuesto_id))


def update_presupuesto_status(presupuesto_id, status):
    with get_connection() as conn:
        conn.execute("UPDATE presupuestos SET status=? WHERE id=?", (status, presupuesto_id))


def update_presupuesto_remito_id(presupuesto_id, remito_id):
    with get_connection() as conn:
        conn.execute("UPDATE presupuestos SET remito_id=? WHERE id=?", (remito_id, presupuesto_id))


def get_all_presupuestos(limit=100, estado=None):
    auto_vencimiento_presupuestos()
    with get_connection() as conn:
        if estado:
            rows = conn.execute(
                "SELECT * FROM presupuestos WHERE status=? ORDER BY id DESC LIMIT ?",
                (estado, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM presupuestos ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def get_presupuestos_count_by_estado():
    auto_vencimiento_presupuestos()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM presupuestos GROUP BY status"
        ).fetchall()
        return {r["status"]: r["cnt"] for r in rows}


def get_presupuesto(presupuesto_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM presupuestos WHERE id=?", (presupuesto_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        return d


def get_presupuestos_by_client(client_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM presupuestos WHERE client_id=? ORDER BY id DESC", (client_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def search_presupuestos(query, estado=None):
    auto_vencimiento_presupuestos()
    q = f"%{query}%"
    with get_connection() as conn:
        if estado:
            rows = conn.execute(
                """SELECT * FROM presupuestos
                   WHERE status=? AND (number LIKE ? OR client_name LIKE ? OR observations LIKE ?)
                   ORDER BY id DESC""",
                (estado, q, q, q),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM presupuestos
                   WHERE number LIKE ? OR client_name LIKE ? OR observations LIKE ?
                   ORDER BY id DESC""",
                (q, q, q),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


# ── Eliminar ───────────────────────────────────────────────────────────────────

def delete_remito(remito_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM remitos WHERE id=?", (remito_id,))


def delete_presupuesto(presupuesto_id):
    """Borra un presupuesto solo si está en estado 'borrador'."""
    with get_connection() as conn:
        presupuesto = conn.execute(
            "SELECT status FROM presupuestos WHERE id=?", (presupuesto_id,)
        ).fetchone()
        if not presupuesto:
            raise ValueError("Presupuesto no encontrado")
        status = dict(presupuesto)["status"] if presupuesto else None
        if status != "borrador":
            raise ValueError(f"No se puede borrar un presupuesto {status}")
        conn.execute("DELETE FROM presupuestos WHERE id=?", (presupuesto_id,))


# ── Actualizar ──────────────────────────────────────────────────────────────────

def update_remito(remito_id, date, client_id, client_name, client_address, client_cuit,
                  client_email, client_phone, items, subtotal, tax_rate, tax_amount,
                  total, observations=""):
    with get_connection() as conn:
        conn.execute(
            """UPDATE remitos
               SET date=?, client_id=?, client_name=?, client_address=?, client_cuit=?,
                   client_email=?, client_phone=?, items=?, subtotal=?, tax_rate=?,
                   tax_amount=?, total=?, observations=?
               WHERE id=?""",
            (
                date, client_id, client_name, client_address, client_cuit,
                client_email, client_phone, json.dumps(items, ensure_ascii=False),
                subtotal, tax_rate, tax_amount, total, observations, remito_id,
            ),
        )


def update_presupuesto(presupuesto_id, date, valid_until, status, client_id, client_name,
                       client_address, client_cuit, client_email, client_phone, items,
                       subtotal, tax_rate, tax_amount, total, observations=""):
    with get_connection() as conn:
        conn.execute(
            """UPDATE presupuestos
               SET date=?, valid_until=?, status=?, client_id=?, client_name=?,
                   client_address=?, client_cuit=?, client_email=?, client_phone=?,
                   items=?, subtotal=?, tax_rate=?, tax_amount=?, total=?, observations=?
               WHERE id=?""",
            (
                date, valid_until, status, client_id, client_name, client_address,
                client_cuit, client_email, client_phone, json.dumps(items, ensure_ascii=False),
                subtotal, tax_rate, tax_amount, total, observations, presupuesto_id,
            ),
        )


# ── Configuración ARCA ── movido a db_arca_config.py, re-exportado arriba ─────


# ── Facturas ────────────────────────────────────────────────────────────────────

def get_next_factura_numero(punto_venta, tipo):
    """Devuelve el próximo número correlativo para tipo+punto_venta."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(numero) FROM facturas WHERE punto_venta=? AND tipo=?",
            (punto_venta, tipo),
        ).fetchone()
        return (row[0] or 0) + 1


def create_factura(tipo, punto_venta, numero, fecha, cliente_cuit, cliente_razon,
                   cliente_iva_cond, items, subtotal, iva_amount, total,
                   concepto=1, cae="", cae_vto="", observaciones="", pdf_path="",
                   cliente_domicilio="", fch_serv_desde="", fch_serv_hasta="",
                   fch_vto_pago="", cbte_asoc_tipo=0, cbte_asoc_pv=0, cbte_asoc_nro=0,
                   condicion_venta="", usuario_id=None):
    """Crea una nueva factura electrónica. `numero` es el número calculado por el
    caller (local o vía ARCA) pero puede haber quedado obsoleto si otra factura
    concurrente para el mismo tipo+punto_venta se creó en el medio (no había
    ningún UNIQUE ni retry — hallazgo cruzado desde la auditoría de Restolibra,
    "race condition en numeración"). Si el INSERT choca contra
    idx_facturas_numero_unico, se recalcula el número y se reintenta — el
    caller debe releer la factura por id (`get_factura`) para conocer el
    número real, nunca asumir que es el que pasó."""
    MAX_INTENTOS = 5
    for intento in range(MAX_INTENTOS):
        try:
            with get_connection() as conn:
                cur = conn.execute(
                    """INSERT INTO facturas
                       (tipo, punto_venta, numero, fecha, cliente_cuit, cliente_razon,
                        cliente_iva_cond, items, subtotal, iva_amount, total, concepto,
                        cae, cae_vto, observaciones, pdf_path, cliente_domicilio,
                        fch_serv_desde, fch_serv_hasta, fch_vto_pago,
                        cbte_asoc_tipo, cbte_asoc_pv, cbte_asoc_nro, condicion_venta, usuario_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (tipo, punto_venta, numero, fecha, cliente_cuit, cliente_razon,
                     cliente_iva_cond, json.dumps(items, ensure_ascii=False), subtotal,
                     iva_amount, total, concepto, cae, cae_vto, observaciones, pdf_path,
                     cliente_domicilio, fch_serv_desde, fch_serv_hasta, fch_vto_pago,
                     cbte_asoc_tipo, cbte_asoc_pv, cbte_asoc_nro, condicion_venta, usuario_id),
                )
                return cur.lastrowid
        except sqlite3.IntegrityError:
            if intento == MAX_INTENTOS - 1:
                raise
            numero = get_next_factura_numero(punto_venta, tipo)


_TIPOS_FACTURA = (1, 6, 11)
_TIPOS_NC      = (3, 8, 13)
_TIPOS_ND      = (2, 7, 12)

_VISTA_TIPOS = {
    "facturas": _TIPOS_FACTURA,
    "nc":       _TIPOS_NC,
    "nd":       _TIPOS_ND,
}


def get_all_facturas(limit=100, vista="facturas"):
    """Obtiene facturas, notas de crédito o notas de débito (últimas primero)."""
    tipos = _VISTA_TIPOS.get(vista, _TIPOS_FACTURA)
    placeholders = ",".join("?" * len(tipos))
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM facturas WHERE tipo IN ({placeholders}) ORDER BY id DESC LIMIT ?",
            (*tipos, limit),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def get_facturas_filtradas(desde="", hasta="", q="", vista="facturas", limit=50, offset=0):
    """Listado de facturas con filtros de fecha, búsqueda y paginación."""
    solo_sin_cobrar = (vista == "sin_cobrar")
    tipos = _VISTA_TIPOS.get("facturas" if solo_sin_cobrar else vista, _TIPOS_FACTURA)
    ph = ",".join("?" * len(tipos))
    conds = [f"f.tipo IN ({ph})"]
    params = list(tipos)
    if desde:
        conds.append("f.fecha >= ?"); params.append(desde)
    if hasta:
        conds.append("f.fecha <= ?"); params.append(hasta)
    if q:
        conds.append("(CAST(f.numero AS TEXT) LIKE ? OR f.cliente_razon LIKE ? OR f.observaciones LIKE ?)")
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    _cc_excl = "AND LOWER(cm.medio_pago) NOT IN ('cuenta corriente','cuenta_corriente')"
    if solo_sin_cobrar:
        conds.append("f.cae != '' AND f.cae IS NOT NULL AND f.cae != 'PENDIENTE'")
        conds.append(f"""
            COALESCE((SELECT SUM(cm.monto) FROM caja_movimientos cm
                      WHERE cm.factura_id=f.id AND cm.tipo='ingreso' {_cc_excl}), 0) < f.total
        """)
    where = " AND ".join(conds)
    cobrada_col = f"""
        COALESCE((SELECT SUM(cm.monto) FROM caja_movimientos cm
                  WHERE cm.factura_id=f.id AND cm.tipo='ingreso' {_cc_excl}), 0) AS total_cobrado
    """
    with get_connection() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM facturas f WHERE {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT f.*, {cobrada_col} FROM facturas f WHERE {where} ORDER BY f.id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["items"] = json.loads(d["items"])
        result.append(d)
    return {"items": result, "total": total}


def get_factura(factura_id):
    """Obtiene una factura por ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM facturas WHERE id=?", (factura_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        return d


def update_factura_cae(factura_id, cae, cae_vto):
    """Actualiza CAE de una factura después de obtenerlo de ARCA."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE facturas SET cae=?, cae_vto=? WHERE id=?",
            (cae, cae_vto, factura_id)
        )


def update_factura_pdf_path(factura_id, pdf_path):
    """Actualiza el path del PDF de la factura."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE facturas SET pdf_path=? WHERE id=?",
            (pdf_path, factura_id)
        )


def search_facturas(query, vista="facturas"):
    """Busca facturas por número, cliente u observaciones."""
    tipos = _VISTA_TIPOS.get(vista, _TIPOS_FACTURA)
    placeholders = ",".join("?" * len(tipos))
    q = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT * FROM facturas
               WHERE tipo IN ({placeholders})
                 AND (numero LIKE ? OR cliente_razon LIKE ? OR observaciones LIKE ?)
               ORDER BY id DESC""",
            (*tipos, q, q, q),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def get_notas_de_factura(tipo, punto_venta, numero, tipos_nota):
    """Devuelve notas (NC o ND) que referencian un comprobante."""
    placeholders = ",".join("?" * len(tipos_nota))
    with get_connection() as conn:
        rows = conn.execute(
            f"""SELECT * FROM facturas
               WHERE tipo IN ({placeholders})
                 AND cbte_asoc_tipo=? AND cbte_asoc_pv=? AND cbte_asoc_nro=?
               ORDER BY id DESC""",
            (*tipos_nota, tipo, punto_venta, numero),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["items"] = json.loads(d["items"])
            result.append(d)
        return result


def get_nc_de_factura(tipo, punto_venta, numero):
    """Devuelve las notas de crédito que anulan un comprobante."""
    return get_notas_de_factura(tipo, punto_venta, numero, _TIPOS_NC)


def get_nd_de_factura(tipo, punto_venta, numero):
    """Devuelve las notas de débito asociadas a un comprobante."""
    return get_notas_de_factura(tipo, punto_venta, numero, _TIPOS_ND)


def get_factura_por_tipo_pv_nro(tipo, punto_venta, numero):
    """Busca un comprobante por tipo + punto de venta + número."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM facturas WHERE tipo=? AND punto_venta=? AND numero=?",
            (tipo, punto_venta, numero),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        return d


def delete_factura(factura_id):
    """Elimina una factura."""
    with get_connection() as conn:
        conn.execute("DELETE FROM facturas WHERE id=?", (factura_id,))


# ── Cajas/Caja ── movido a db_caja.py, re-exportado arriba ────────────────────


# ── MercadoPago pagos ──────────────────────────────────────────────────────────

def get_mp_pago(mp_payment_id: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM mp_pagos WHERE mp_payment_id=?", (str(mp_payment_id),)
        ).fetchone()
        return dict(row) if row else None


def create_mp_pago(mp_payment_id: str, status: str, monto: float,
                   payer_email: str, payer_name: str, factura_id=None,
                   estado_factura: str = None, payment_type: str = None,
                   payment_method: str = None, descripcion_mp: str = None,
                   payer_id_type: str = None, payer_id_number: str = None):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO mp_pagos
               (mp_payment_id, status, monto, payer_email, payer_name, factura_id,
                estado_factura, payment_type, payment_method, descripcion_mp,
                payer_id_type, payer_id_number)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(mp_payment_id), status, float(monto), payer_email, payer_name, factura_id,
             estado_factura, payment_type, payment_method, descripcion_mp,
             payer_id_type, payer_id_number),
        )
        return cur.lastrowid


def get_mp_pago_by_id(id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM mp_pagos WHERE id=?", (id,)).fetchone()
        return dict(row) if row else None


def get_mp_pagos_by_estado(estado: str):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM mp_pagos WHERE estado_factura=? ORDER BY created_at DESC",
            (estado,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_mp_pagos_historial(limit: int = 50):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM mp_pagos
               WHERE estado_factura IN ('facturado', 'ignorado')
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_mp_pago_estado(id: int, estado: str, factura_id=None):
    with get_connection() as conn:
        if factura_id is not None:
            conn.execute(
                "UPDATE mp_pagos SET estado_factura=?, factura_id=? WHERE id=?",
                (estado, factura_id, id),
            )
        else:
            conn.execute(
                "UPDATE mp_pagos SET estado_factura=? WHERE id=?",
                (estado, id),
            )


def get_client_by_email(email: str):
    normalized = (email or "").strip().lower()
    if not normalized:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE LOWER(email)=? ORDER BY activo DESC, id DESC LIMIT 1",
            (normalized,),
        ).fetchone()
        return dict(row) if row else None


def get_client_by_cuit(cuit: str):
    """Busca cliente por CUIT normalizando guiones (ej: 20317819162 == 20-31781916-2).
    Si hay más de un cliente con el mismo CUIT (duplicado), prioriza el activo
    y, entre iguales, el más reciente."""
    normalized = (cuit or "").replace("-", "").strip()
    if not normalized:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM clients WHERE REPLACE(cuit_dni, '-', '') = ? ORDER BY activo DESC, id DESC LIMIT 1",
            (normalized,),
        ).fetchone()
    return dict(row) if row else None


# ── Alias de facturación MP (excepciones payer CUIT/email → cliente) ───────────

def _normalizar_alias(tipo: str, valor: str) -> str:
    valor = (valor or "").strip()
    if tipo == "cuit":
        return valor.replace("-", "")
    return valor.lower()


def crear_alias_facturacion(tipo: str, valor: str, cliente_id: int) -> int:
    """Registra que los pagos de MP identificados por este CUIT o email deben
    facturarse al cliente indicado, en vez de al cliente que coincide directo
    con esos datos (o de crear uno nuevo)."""
    if tipo not in ("cuit", "email"):
        raise ValueError("Tipo de alias inválido.")
    valor_norm = _normalizar_alias(tipo, valor)
    if not valor_norm:
        raise ValueError("El valor del alias no puede estar vacío.")
    if not get_client(cliente_id):
        raise ValueError("El cliente destino no existe.")
    with get_connection() as conn:
        existente = conn.execute(
            "SELECT fa.id, c.name FROM facturacion_alias fa JOIN clients c ON c.id = fa.cliente_id "
            "WHERE fa.tipo=? AND fa.valor=? AND fa.activo=1",
            (tipo, valor_norm),
        ).fetchone()
        if existente:
            raise ValueError(
                f'Ese {tipo.upper()} ya está asignado a "{existente["name"]}". '
                "Eliminá ese alias primero si querés reasignarlo."
            )
        cur = conn.execute(
            "INSERT INTO facturacion_alias (tipo, valor, cliente_id) VALUES (?,?,?)",
            (tipo, valor_norm, cliente_id),
        )
        return cur.lastrowid


def get_alias_facturacion_by_cliente(cliente_id: int) -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM facturacion_alias WHERE cliente_id=? AND activo=1 ORDER BY created_at",
            (cliente_id,),
        ).fetchall()]


def eliminar_alias_facturacion(alias_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM facturacion_alias WHERE id=?", (alias_id,))


def get_cliente_por_alias_pago(payer_email: str = "", payer_cuit: str = ""):
    """Si el CUIT o el email del pagador tienen un alias de facturación
    configurado, devuelve el cliente destino de ese alias."""
    cuit_norm  = _normalizar_alias("cuit", payer_cuit)
    email_norm = _normalizar_alias("email", payer_email)
    with get_connection() as conn:
        row = None
        if cuit_norm:
            row = conn.execute(
                "SELECT cliente_id FROM facturacion_alias WHERE tipo='cuit' AND valor=? AND activo=1",
                (cuit_norm,),
            ).fetchone()
        if not row and email_norm:
            row = conn.execute(
                "SELECT cliente_id FROM facturacion_alias WHERE tipo='email' AND valor=? AND activo=1",
                (email_norm,),
            ).fetchone()
    return get_client(row["cliente_id"]) if row else None


def resolver_cliente_pago(payer_email: str = "", payer_cuit: str = ""):
    """Resuelve a qué cliente corresponde facturar un pago de MP: primero
    respeta un alias explícito (excepción configurada), y si no hay,
    matchea al cliente cuyo email o CUIT coincide con el del pagador."""
    alias = get_cliente_por_alias_pago(payer_email, payer_cuit)
    if alias:
        return alias
    client = get_client_by_email(payer_email) if payer_email else None
    if not client and payer_cuit:
        client = get_client_by_cuit(payer_cuit)
    return client


# ── MercadoPago movimientos (transferencias bancarias entrantes) ───────────────

def get_mp_movimiento_by_mp_id(mp_movement_id: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM mp_movimientos WHERE mp_movement_id=?", (str(mp_movement_id),)
        ).fetchone()
        return dict(row) if row else None


def create_mp_movimiento(mp_movement_id: str, tipo: str, monto: float, fecha: str,
                         descripcion: str = "", origen_nombre: str = "",
                         origen_banco: str = "", origen_cbu: str = "",
                         payer_email: str = "", payer_name: str = "",
                         payer_id_type: str = "", payer_id_number: str = "",
                         estado_factura: str = "pendiente"):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO mp_movimientos
               (mp_movement_id, tipo, monto, fecha, descripcion, origen_nombre, origen_banco,
                origen_cbu, payer_email, payer_name, payer_id_type, payer_id_number, estado_factura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(mp_movement_id), tipo, float(monto), fecha, descripcion,
             origen_nombre, origen_banco, origen_cbu,
             payer_email, payer_name, payer_id_type, payer_id_number, estado_factura),
        )
        return cur.lastrowid


def get_mp_movimiento_by_id(id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM mp_movimientos WHERE id=?", (id,)).fetchone()
        return dict(row) if row else None


def get_mp_movimientos_by_estado(estado: str):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM mp_movimientos WHERE estado_factura=? ORDER BY fecha DESC, created_at DESC",
            (estado,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_mp_movimientos_historial(limit: int = 50):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM mp_movimientos
               WHERE estado_factura IN ('facturado', 'ignorado')
               ORDER BY fecha DESC, created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_mp_movimiento_datos(id: int, payer_email: str = None, payer_name: str = None,
                               payer_id_type: str = None, payer_id_number: str = None):
    fields = {}
    if payer_email is not None:
        fields["payer_email"] = payer_email
    if payer_name is not None:
        fields["payer_name"] = payer_name
    if payer_id_type is not None:
        fields["payer_id_type"] = payer_id_type
    if payer_id_number is not None:
        fields["payer_id_number"] = payer_id_number
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE mp_movimientos SET {set_clause} WHERE id=?",
            (*fields.values(), id),
        )


def update_mp_movimiento_estado(id: int, estado: str, factura_id=None):
    with get_connection() as conn:
        if factura_id is not None:
            conn.execute(
                "UPDATE mp_movimientos SET estado_factura=?, factura_id=? WHERE id=?",
                (estado, factura_id, id),
            )
        else:
            conn.execute(
                "UPDATE mp_movimientos SET estado_factura=? WHERE id=?",
                (estado, id),
            )


def get_mp_pending_count() -> int:
    with get_connection() as conn:
        return conn.execute(
            """SELECT
               (SELECT COUNT(*) FROM mp_pagos WHERE estado_factura='pendiente') +
               (SELECT COUNT(*) FROM mp_movimientos WHERE estado_factura='pendiente')"""
        ).fetchone()[0]


def vincular_mp_pago_cliente(mp_pago_id: int, payer_email: str, payer_name: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE mp_pagos SET payer_email=?, payer_name=? WHERE id=?",
            (payer_email, payer_name, mp_pago_id),
        )


# ── Dashboard ── movido a db_dashboard.py, re-exportado arriba ────────────────

# ── Usuarios ── movido a db_usuarios.py, re-exportado arriba ──────────────────

# ── Depósitos/Categorías de producto/Productos ── movido a db_productos.py, re-exportado arriba ─

# ── Turnos de caja ── movido a db_turnos.py, re-exportado arriba ──────────────


# ── Stock ─────────────────────────────────────────────────────────────────────

def add_movimiento_stock(producto_id: int, tipo: str, cantidad: float,
                         referencia: str = "", fecha: str = "",
                         venta_id: int | None = None,
                         usuario_id: int | None = None,
                         deposito_id: int | None = None,
                         conn: sqlite3.Connection | None = None):
    """Agrega un movimiento de stock. cantidad positiva=entrada, negativa=salida."""
    from datetime import date as _date
    _fecha = fecha or _date.today().isoformat()
    _deposito = deposito_id or get_default_deposito_id()
    cm = contextlib.nullcontext(conn) if conn is not None else get_connection()
    with cm as c:
        c.execute(
            """INSERT INTO movimientos_stock
               (producto_id, tipo, cantidad, referencia, venta_id, usuario_id, fecha, deposito_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (producto_id, tipo, cantidad, referencia, venta_id, usuario_id, _fecha, _deposito),
        )


def get_stock_actual(producto_id: int) -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(cantidad),0) FROM movimientos_stock WHERE producto_id=?",
            (producto_id,),
        ).fetchone()
    return float(row[0])


def get_stock_todos() -> list[dict]:
    """Devuelve todos los productos con su stock actual."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT p.id, p.codigo, p.nombre, p.unidad, p.categoria,
                   p.stock_minimo, p.activo,
                   COALESCE(SUM(m.cantidad), 0) AS stock_actual
            FROM productos p
            LEFT JOIN movimientos_stock m ON m.producto_id = p.id
            WHERE p.activo = 1
            GROUP BY p.id
            ORDER BY p.nombre
        """).fetchall()
    return [dict(r) for r in rows]


def get_movimientos_stock(producto_id: int | None = None,
                          desde: str = "", hasta: str = "",
                          limit: int = 200) -> list[dict]:
    with get_connection() as conn:
        where, params = [], []
        if producto_id:
            where.append("m.producto_id = ?"); params.append(producto_id)
        if desde:
            where.append("m.fecha >= ?"); params.append(desde)
        if hasta:
            where.append("m.fecha <= ?"); params.append(hasta)
        sql = """SELECT m.*, p.nombre AS producto_nombre, p.unidad
                 FROM movimientos_stock m
                 JOIN productos p ON p.id = m.producto_id"""
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY m.fecha DESC, m.id DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def ajustar_stock(producto_id: int, stock_nuevo: float, referencia: str,
                  usuario_id: int | None = None, fecha: str = ""):
    """Crea un movimiento de ajuste para llevar el stock al valor indicado."""
    actual = get_stock_actual(producto_id)
    delta  = round(stock_nuevo - actual, 4)
    if delta == 0:
        return
    add_movimiento_stock(
        producto_id=producto_id, tipo="ajuste",
        cantidad=delta, referencia=referencia,
        usuario_id=usuario_id, fecha=fecha,
    )


def descontar_stock_venta(venta_id: int, items: list, fecha: str = "",
                           usuario_id: int | None = None,
                           conn: sqlite3.Connection | None = None):
    """Descuenta stock por cada ítem de la venta que tenga producto_id."""
    for item in items:
        pid = item.get("producto_id")
        if not pid:
            continue
        add_movimiento_stock(
            producto_id=pid, tipo="venta",
            cantidad=-abs(float(item.get("qty", 0))),
            referencia=f"Venta ID {venta_id}",
            venta_id=venta_id, usuario_id=usuario_id, fecha=fecha,
            conn=conn,
        )


# ── Ventas ────────────────────────────────────────────────────────────────────

def get_next_venta_numero(conn: sqlite3.Connection | None = None) -> str:
    """Si se pasa `conn`, calcula el número dentro de esa transacción (para no
    chocar con otra venta concurrente) — ver `crear_venta_directa`. Sin `conn`,
    sigue siendo best-effort (uso legacy)."""
    cm = contextlib.nullcontext(conn) if conn is not None else get_connection()
    with cm as c:
        row = c.execute(
            "SELECT numero FROM ventas ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row:
        try:
            n = int(row["numero"].split("-")[-1]) + 1
        except (ValueError, IndexError):
            n = 1
    else:
        n = 1
    return f"V-{n:05d}"


def create_venta(numero: str, fecha: str, items: list, subtotal: float,
                 descuento: float, total: float, cliente_id: int | None,
                 cliente_nombre: str, usuario_id: int | None,
                 observaciones: str = "", estado: str = "cobrada",
                 conn: sqlite3.Connection | None = None) -> int:
    cm = contextlib.nullcontext(conn) if conn is not None else get_connection()
    with cm as c:
        cur = c.execute(
            """INSERT INTO ventas
               (numero, fecha, items, subtotal, descuento, total,
                cliente_id, cliente_nombre, usuario_id, observaciones, estado)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (numero, fecha, json.dumps(items, ensure_ascii=False),
             subtotal, descuento, total,
             cliente_id, cliente_nombre, usuario_id, observaciones, estado),
        )
        return cur.lastrowid


def add_venta_pago(venta_id: int, medio: str, monto: float, referencia: str = "",
                   conn: sqlite3.Connection | None = None):
    cm = contextlib.nullcontext(conn) if conn is not None else get_connection()
    with cm as c:
        c.execute(
            "INSERT INTO ventas_pagos (venta_id, medio, monto, referencia) VALUES (?,?,?,?)",
            (venta_id, medio, monto, referencia),
        )


def crear_venta_directa(fecha: str, items: list, subtotal: float, descuento: float,
                        total: float, cliente_id: int | None, cliente_nombre: str,
                        usuario_id: int | None, observaciones: str, estado: str,
                        pagos: list[dict], stock_habilitado: bool) -> int:
    """Crea una venta ("Nueva venta" del módulo Ventas) con sus pagos, un
    movimiento de caja por cada medio, descuento de stock y vinculación al
    turno activo — todo en una única transacción. Antes, cada paso abría su
    propia conexión: si algo fallaba a mitad de camino quedaba una venta
    huérfana sin pagos/caja/stock, y dos submits casi simultáneos (doble
    click) podían duplicar todo. Mismo fix que Restolibra (fork downstream).

    El número de venta se calcula recién al entrar a la transacción; si dos
    o más ventas concurrentes chocan en el mismo número (`UNIQUE` en
    `ventas.numero`), se reintenta con un número fresco. Cada intento
    fallido reduce la contención en al menos uno (el que ganó ese round ya
    commiteó), así que el número de reintentos necesarios está acotado por
    la cantidad de submits realmente simultáneos — en la práctica 1 (doble
    click)."""
    MAX_INTENTOS = 10
    for intento in range(MAX_INTENTOS):
        with get_connection() as conn:
            try:
                numero = get_next_venta_numero(conn=conn)
                venta_id = create_venta(
                    numero=numero, fecha=fecha, items=items,
                    subtotal=subtotal, descuento=descuento, total=total,
                    cliente_id=cliente_id, cliente_nombre=cliente_nombre,
                    usuario_id=usuario_id, observaciones=observaciones, estado=estado,
                    conn=conn,
                )
                for p in pagos:
                    add_venta_pago(venta_id, p["medio"], p["monto"],
                                   p.get("referencia", ""), conn=conn)
                    label = MEDIOS_PAGO_LABELS.get(p["medio"], p["medio"])
                    create_caja_movimiento(
                        fecha=fecha, tipo="ingreso",
                        concepto=f"Venta {numero} — {label}",
                        monto=p["monto"], referencia=p.get("referencia", ""),
                        medio_pago=p["medio"], usuario_id=usuario_id, conn=conn,
                    )

                if stock_habilitado:
                    descontar_stock_venta(venta_id, items, fecha=fecha,
                                          usuario_id=usuario_id, conn=conn)

                if usuario_id:
                    turno = get_turno_activo(usuario_id, conn=conn)
                    if turno:
                        vincular_venta_turno(venta_id, turno["id"], conn=conn)

                conn.commit()
                return venta_id
            except sqlite3.IntegrityError:
                conn.rollback()
                if intento < MAX_INTENTOS - 1:
                    continue
                raise
            except Exception:
                conn.rollback()
                raise
    raise RuntimeError("No se pudo generar un número de venta único")


def get_all_ventas(desde: str = "", hasta: str = "", q: str = "",
                   tab: str = "todas", limit: int = 100, offset: int = 0) -> list[dict]:
    with get_connection() as conn:
        where, params = [], []
        if desde:
            where.append("v.fecha >= ?"); params.append(desde)
        if hasta:
            where.append("v.fecha <= ?"); params.append(hasta)
        if q:
            where.append("(v.numero LIKE ? OR v.cliente_nombre LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        if tab == "sin_facturar":
            where.append("v.factura_id IS NULL AND v.estado != 'anulada'")
        elif tab == "facturadas":
            where.append("v.factura_id IS NOT NULL")
        sql = """SELECT v.*,
                        GROUP_CONCAT(p.medio || ':' || p.monto, '|') AS pagos_raw,
                        f.tipo    AS fac_tipo,
                        f.punto_venta AS fac_pv,
                        f.numero  AS fac_numero
                 FROM ventas v
                 LEFT JOIN ventas_pagos p ON p.venta_id = v.id
                 LEFT JOIN facturas f ON f.id = v.factura_id"""
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " GROUP BY v.id ORDER BY v.fecha DESC, v.id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = conn.execute(sql, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["items"] = json.loads(d["items"])
        d["pagos"] = _parse_pagos_raw(d.pop("pagos_raw", "") or "")
        if d.get("fac_tipo") and d.get("fac_numero"):
            pv  = str(d.get("fac_pv") or 0).zfill(4)
            num = str(d["fac_numero"]).zfill(8)
            d["factura_display"] = f"{d['fac_tipo']} {pv}-{num}"
        else:
            d["factura_display"] = None
        result.append(d)
    return result


def get_venta(vid: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM ventas WHERE id=?", (vid,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["items"] = json.loads(d["items"])
        pagos = conn.execute(
            "SELECT * FROM ventas_pagos WHERE venta_id=? ORDER BY id", (vid,)
        ).fetchall()
        d["pagos"] = [dict(p) for p in pagos]
    return d


def _parse_pagos_raw(raw: str) -> list[dict]:
    pagos = []
    for part in raw.split("|"):
        if ":" in part:
            medio, monto = part.split(":", 1)
            try:
                pagos.append({"medio": medio, "monto": float(monto)})
            except ValueError:
                pass
    return pagos


def anular_venta(vid: int, usuario_id: int | None = None) -> None:
    """Anula una venta: repone el stock que se había descontado, revierte con
    un egreso cada movimiento de caja generado por sus pagos y, si tenía un
    pago a cuenta corriente, acredita la deuda del cliente vía `create_cc_pago`
    (mismo mecanismo que ya usa el cobro de una factura a Cuenta Corriente en
    `facturas.py`). Todo en una única transacción; no-op si la venta ya
    estaba anulada, para no revertir dos veces si se reintenta la acción.
    Mismo fix que Restolibra (fork downstream) — antes esto solo hacía
    `UPDATE ventas SET estado='anulada'`, sin revertir nada."""
    with get_connection() as conn:
        try:
            venta = conn.execute("SELECT * FROM ventas WHERE id=?", (vid,)).fetchone()
            if not venta:
                raise ValueError("Venta inexistente")
            if venta["estado"] == "anulada":
                return

            fecha = _ar_now().split(" ")[0]

            for m in conn.execute(
                "SELECT producto_id, cantidad, deposito_id FROM movimientos_stock "
                "WHERE venta_id=? AND tipo='venta'", (vid,)
            ).fetchall():
                add_movimiento_stock(
                    producto_id=m["producto_id"], tipo="anulacion",
                    cantidad=-m["cantidad"], referencia=f"Anulación venta ID {vid}",
                    venta_id=vid, usuario_id=usuario_id, fecha=fecha,
                    deposito_id=m["deposito_id"], conn=conn,
                )

            for p in conn.execute(
                "SELECT id, medio, monto FROM ventas_pagos WHERE venta_id=?", (vid,)
            ).fetchall():
                label = MEDIOS_PAGO_LABELS.get(p["medio"], p["medio"])
                create_caja_movimiento(
                    fecha=fecha, tipo="egreso",
                    concepto=f"Anulación venta {venta['numero']} — {label}",
                    monto=p["monto"], referencia=f"anulacion:venta:{vid}:pago:{p['id']}",
                    medio_pago=p["medio"], usuario_id=usuario_id, conn=conn,
                )
                if p["medio"] == "cuenta_corriente" and venta["cliente_id"]:
                    create_cc_pago(
                        cliente_id=venta["cliente_id"], monto=p["monto"], fecha=fecha,
                        concepto=f"Anulación venta {venta['numero']}",
                        referencia="", medio_pago="cuenta_corriente",
                        caja_id=None, usuario_id=usuario_id, conn=conn,
                    )

            conn.execute("UPDATE ventas SET estado='anulada' WHERE id=?", (vid,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def vincular_venta_factura(vid: int, factura_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE ventas SET factura_id=? WHERE id=?", (factura_id, vid))


def vincular_venta_remito(vid: int, remito_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE ventas SET remito_id=? WHERE id=?", (remito_id, vid))


# ── Log de actividad/autenticación ── movido a db_logs.py, re-exportado arriba ─


# ── Módulos ── movido a db_modulos.py, re-exportado arriba ────────────────────

# ── Reportes ── movido a db_reportes.py, re-exportado arriba ──────────────────
# (las 4 funciones de ventas/MP que estaban bajo este header quedan abajo,
# no son reportes — pendientes para cuando se extraiga el dominio ventas/MP)


def set_venta_mp_order(venta_id: int, mp_order_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE ventas SET mp_order_id=? WHERE id=?",
            (mp_order_id, venta_id),
        )
        conn.commit()


def set_venta_mp_payment(venta_id: int, mp_payment_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE ventas SET mp_payment_id=? WHERE id=?",
            (mp_payment_id, venta_id),
        )
        conn.commit()


def get_venta_by_mp_order(mp_order_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM ventas WHERE mp_order_id=?", (mp_order_id,)
        ).fetchone()
        return dict(row) if row else None


def add_venta_pago_referencia_mp(venta_id: int, payment_id: str) -> None:
    """Actualiza la referencia del pago MP/billetera de la venta con el payment_id."""
    with get_connection() as conn:
        # Actualizar referencia en el pago existente de medio mercadopago/billetera/cuenta_dni
        conn.execute(
            """UPDATE ventas_pagos SET referencia=?
               WHERE venta_id=? AND medio IN ('mercadopago','billetera','cuenta_dni','qr')
               AND (referencia IS NULL OR referencia='')""",
            (f"MP#{payment_id}", venta_id),
        )
        conn.commit()


# ── Categorías de egreso/Proveedores/Egresos ── movido a db_egresos.py, re-exportado arriba ──


# ── Tesorería ── movido a db_tesoreria.py, re-exportado arriba ────────────────

# ── Cuenta corriente por cliente ── movido a db_cuenta_corriente.py, re-exportado arriba ─


# ── Listas de precios ── movido a db_listas_precio.py, re-exportado arriba ────


# ── Libros IVA ── movido a db_libros_iva.py, re-exportado arriba ──────────────
