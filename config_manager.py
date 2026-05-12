import json
import os

_DATA_DIR   = os.environ.get("DATA_DIR", os.path.dirname(__file__))
CONFIG_PATH = os.path.join(_DATA_DIR, "config.json")

_DEFAULTS = {
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
