import json
import os

_DATA_DIR   = os.environ.get("DATA_DIR", os.path.dirname(__file__))
CONFIG_PATH = os.path.join(_DATA_DIR, "config.json")

_DEFAULTS = {
    # Estado del servicio (gestionado desde panel_admin.py o config web)
    "servicio_estado":        "activo",   # activo | pausado | suspendido
    "servicio_mensaje":       "",         # mensaje personalizado opcional
    "empresa_nombre":         "",
    "empresa_direccion":      "",
    "empresa_cuit":           "",
    "empresa_telefono":       "",
    "empresa_email":          "",
    "empresa_iibb":           "",
    "empresa_iva_condition":       "Monotributista",
    "empresa_inicio_actividades":  "",
    "logo_path":                   "",
    # MercadoPago
    "mp_access_token":        "",
    "mp_webhook_secret":      "",
    "mp_concepto_descripcion": "Suscripcion mensual",
    "mp_iva_rate":            "0",
    # Email / SMTP
    "email_smtp_host":        "",
    "email_smtp_port":        "587",
    "email_smtp_user":        "",
    "email_smtp_password":    "",
    "email_from":             "",
    "email_from_name":        "",
    # Impresora de tickets (ticketeadora térmica)
    "ticket_ancho_mm":        "80",      # 58 | 80
    "ticket_fuente_size":     "9",       # puntos
    "ticket_mostrar_logo":    "0",       # 0 | 1
    "ticket_linea_corte":     "1",       # imprimir línea de corte al final
    "ticket_pie":             "",        # texto libre al pie (ej: "¡Gracias por su compra!")
}


def load():
    if not os.path.exists(CONFIG_PATH):
        return _DEFAULTS.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**_DEFAULTS, **data}
    except Exception:
        return _DEFAULTS.copy()


def save(data):
    merged = {**_DEFAULTS, **data}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
