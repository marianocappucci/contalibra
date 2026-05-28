# Contalibra

Sistema de gestión para comercios y PyMEs argentinas. Facturación electrónica
ARCA (ex-AFIP), ventas, caja, stock, reportes y más. Arquitectura multi-tenant:
cada cliente corre en su propio contenedor Docker con base de datos aislada.

## Módulos disponibles

| Módulo | Plan | Descripción |
|--------|------|-------------|
| Clientes | Básico | ABM de clientes con historial |
| Ventas | Básico | Punto de venta con múltiples medios de pago y recibo PDF |
| Caja | Básico | Movimientos de caja y turnos de cajero |
| Facturación | Estándar | Facturas electrónicas A/B/C vía ARCA (WSAA + WSFEv1), cobro parcial y recibo PDF |
| Remitos | Estándar | Remitos de entrega (sin precios) con PDF |
| Presupuestos | Estándar | Presupuestos con conversión a remito/factura |
| Productos | Estándar | Catálogo de productos con precios |
| Egresos | Estándar | Registro de gastos con categorías, IVA y seguimiento de pagos |
| Proveedores | Estándar | ABM de proveedores vinculados a egresos |
| Stock | Premium | Control de inventario con alertas de mínimo |
| Depósitos | Premium | Múltiples depósitos con transferencias de stock |
| Reportes | Estándar | Ventas, medios de pago, top productos, caja |
| Tesorería | Estándar | Saldo de múltiples cuentas bancarias/efectivo, movimientos y transferencias |

## Stack técnico

| Componente | Tecnología |
|------------|------------|
| Backend | Python 3.12 + FastAPI |
| Base de datos | SQLite (WAL mode) — una DB por cliente |
| Templates | Jinja2 |
| PDFs | fpdf2 (A4 y formato ticket 58/80mm) |
| Facturación ARCA | WSAA + WSFEv1 (certificado digital) |
| Infraestructura | Docker + Nginx Proxy Manager |
| Auth | Cookies firmadas con itsdangerous + PBKDF2-SHA256 |

## Inicio rápido

Ver **[OPERACIONES.md](OPERACIONES.md)** para la guía completa de:

- Setup inicial del servidor
- Alta de un cliente nuevo (`nuevo_cliente.py`)
- Despliegue de actualizaciones
- Backup y restauración
- Gestión del estado del servicio (pausar/suspender por no pago)

## Estructura del proyecto

```
contalibra/
├── web/                    ← aplicación FastAPI
│   ├── app.py              ← entry point y middleware
│   ├── auth.py             ← autenticación
│   ├── routers/            ← un router por módulo
│   └── templates/          ← Jinja2 (base.html + por módulo)
├── scripts/
│   ├── nuevo_cliente.py    ← onboarding de cliente nuevo
│   ├── panel_admin.py      ← gestión de todos los clientes
│   ├── npm_setup.py        ← configuración de Nginx Proxy Manager
│   └── npm_api.py          ← cliente HTTP para NPM
├── database.py             ← capa de datos SQLite
├── config_manager.py       ← gestión de config.json por cliente
├── pdf_generator.py        ← PDFs A4
├── ticket_generator.py     ← PDFs para ticketeadoras térmicas
├── Dockerfile
├── requirements.txt
├── OPERACIONES.md          ← guía de operaciones del servidor
└── GUIA_CERTIFICADO_ARCA.md
```

## Licencia

Uso privado — Mariano Cappucci.
