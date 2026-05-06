# Contalibra

Sistema de gestión contable para PyMEs argentinas. Permite emitir remitos, presupuestos y facturas electrónicas integradas con ARCA (ex-AFIP), con generación de PDFs y base de datos local.

## Funcionalidades

### Remitos
- Creación, edición y eliminación de remitos numerados automáticamente
- Carga de ítems con cantidad, descripción, precio unitario e IVA configurable
- Generación de PDF con logo, datos del cliente y detalle de productos
- Búsqueda y listado con filtros
- Conversión de presupuesto aceptado a remito en un clic

### Presupuestos
- Creación de presupuestos con fecha de validez
- Estados: pendiente / aceptado / rechazado
- Generación de PDF
- Conversión directa a remito cuando el cliente acepta

### Facturación electrónica (ARCA)
- Emisión de Facturas A y B vía WSAA + WSFEv1 (webservices de ARCA)
- Obtención de CAE en línea
- Generación de PDF con formato legal: encabezado, tabla de ítems, caja CAE y código QR
- Soporte multi-empresa con configuración de certificados y punto de venta por empresa

### Clientes
- ABM de clientes con nombre, domicilio, CUIT/DNI, email y teléfono
- Historial de remitos y presupuestos por cliente

## Interfaz

La aplicación cuenta con dos modos de uso:

- **GUI** (`gui.py`) — Interfaz gráfica con PyQt5, sidebar de navegación, tablas y formularios
- **CLI** (`main.py`) — Menú interactivo en terminal usando `rich`

## Stack técnico

| Componente | Tecnología |
|------------|------------|
| Lenguaje | Python 3.9+ |
| Base de datos | SQLite (`contalibra.db`) |
| GUI | PyQt5 |
| CLI | rich |
| PDFs | fpdf2 |
| Facturación ARCA | pyafipws (WSAA + WSFEv1) |

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/marianocappucci/contalibra.git
cd contalibra

# Crear entorno virtual e instalar dependencias base
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Para facturación electrónica (requiere Python 3.9)
pip install pyafipws pyqt5 qrcode pillow
```

## Uso

```bash
# Interfaz gráfica
python3 gui.py

# Menú de consola
python3 main.py
```

La base de datos se crea automáticamente al primer inicio.

## Configuración ARCA

Para habilitar la facturación electrónica se necesita:

1. Certificado digital emitido por ARCA (ver `GUIA_CERTIFICADO_ARCA.md`)
2. Clave privada asociada al certificado
3. Punto de venta habilitado en ARCA para el CUIT correspondiente

La configuración se carga desde la sección **ARCA Config** dentro de la GUI.

## Estructura del proyecto

```
contalibra/
├── gui.py                  # Interfaz gráfica principal (PyQt5)
├── gui_facturas.py         # Módulo GUI de facturas electrónicas
├── arca_gui.py             # Módulo GUI de configuración ARCA
├── main.py                 # Interfaz CLI
├── database.py             # Capa de acceso a datos (SQLite)
├── pdf_generator.py        # Generador de PDF para remitos
├── pdf_factura.py          # Generador de PDF para facturas (formato ARCA)
├── facturacion_arca.py     # Integración WSAA + WSFEv1
├── requirements.txt        # Dependencias base
├── GUIA_CERTIFICADO_ARCA.md
└── GUIA_RAPIDA_FACTURACION.md
```

## Licencia

Uso privado — Compulibra.
