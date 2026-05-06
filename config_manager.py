import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

_DEFAULTS = {
    "empresa_nombre":    "",
    "empresa_direccion": "",
    "empresa_cuit":      "",
    "empresa_telefono":  "",
    "empresa_email":     "",
    "empresa_iibb":      "",
    "logo_path":         "",
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
