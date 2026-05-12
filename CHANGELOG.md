# Changelog

## v1.0.0 — 2026-05-12

Versión inicial estable. Base completa del sistema Contalibra.

### Módulos incluidos

| Módulo | Descripción |
|--------|-------------|
| Facturación | Facturas A/B/C, Notas de Crédito y Débito con autorización ARCA (AFIP) |
| Remitos | Generación y gestión de remitos con PDF |
| Presupuestos | Presupuestos con conversión a remito/factura y PDF |
| Clientes | ABM de clientes con historial |
| Caja | Registro de movimientos de caja (ingresos/egresos), integración con MercadoPago |
| Config | Configuración de empresa, ARCA/AFIP, logo, condiciones de pago |
| Dashboard | Resumen financiero con totales del período |
| Multi-usuario | Roles admin y operador, hash PBKDF2-SHA256, sesiones con itsdangerous |

### Infraestructura

- Contenedor Docker por cliente (imagen `contalibra:latest`)
- Script de onboarding: `scripts/nuevo_cliente.py`
- Panel de administración CLI: `scripts/panel_admin.py`
- Proxy SSL automático via Nginx Proxy Manager API: `scripts/npm_api.py`, `scripts/npm_setup.py`

### Integraciones

- **ARCA (AFIP)**: WSAA (autenticación con certificado digital) + WSFE (autorización electrónica) + WSPadron A4
- **MercadoPago**: webhook de notificaciones, registro automático en caja
- **Email**: envío de comprobantes PDF por SMTP

### Stack técnico

- Backend: Python 3.11, FastAPI, SQLite, itsdangerous
- PDF: fpdf2 2.8.7
- Frontend: Bootstrap 5.3, Bootstrap Icons
- Deploy: Docker, Nginx Proxy Manager, Let's Encrypt
