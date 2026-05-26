import os
from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _moneda(value, decimals=2):
    try:
        s = f"{float(value):,.{decimals}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value)


def _entero(value):
    try:
        return str(int(round(float(value))))
    except (ValueError, TypeError):
        return str(value)


templates = Jinja2Templates(directory=_TEMPLATES_DIR)
templates.env.filters["moneda"]  = lambda v: _moneda(v, 2)
templates.env.filters["moneda0"] = lambda v: _moneda(v, 0)
templates.env.filters["entero"]  = _entero
