import json
import os

_DATA_DIR   = os.environ.get("DATA_DIR", os.path.dirname(__file__))
CONFIG_PATH = os.path.join(_DATA_DIR, "config.json")
LOGO_DIR    = os.path.join(_DATA_DIR, "logos")

_LOGO_EXTS = (".png", ".jpg", ".jpeg", ".webp")

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
    "mp_concepto_descripcion": "Cobro con Mercadopago",
    "mp_iva_rate":            "0",
    # MercadoPago QR Dinámico (punto de venta presencial)
    "mp_user_id":             "",   # ID numérico del vendedor en MP
    "mp_pos_id":              "",   # External ID del POS creado en MP
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


def resolve_logo_path(cfg=None):
    """Devuelve la ruta a un archivo de logo existente, o "" si no hay ninguno.

    El "logo_path" guardado en config es una ruta absoluta que puede quedar
    obsoleta: hasta la migración de LOGO_DIR a DATA_DIR (2026-07-01) los logos se
    guardaban en /app/logos, y ese valor quedó persistido en configuraciones
    viejas aunque el archivo real ahora viva en DATA_DIR/logos. Si el path
    guardado no existe, se cae al logo más reciente encontrado en LOGO_DIR.
    """
    cfg = cfg if cfg is not None else load()
    p = (cfg.get("logo_path") or "").strip()
    if p and os.path.exists(p):
        return p
    if os.path.isdir(LOGO_DIR):
        cands = [os.path.join(LOGO_DIR, f) for f in os.listdir(LOGO_DIR)
                 if f.lower().startswith("logo") and f.lower().endswith(_LOGO_EXTS)]
        if cands:
            return max(cands, key=os.path.getmtime)
    return ""
