"""
Shim: la lógica del backoffice ahora vive en libracore.admin.app. Se
ejecuta:
    uvicorn admin.app:app --host 0.0.0.0 --port 8000
desde la raíz del repo, con acceso al socket Docker y al directorio
clientes/.
"""
import os

from libracore.admin.app import create_admin_app

from admin import auth, services
from admin.templates_config import templates
from admin.routers import clientes as clientes_router

# `app/web/static` desde el re-empaquetado del 2026-07-31 (antes era
# `web/static`). El backoffice NO es parte del paquete -- corre fuera de
# Docker, con systemd y su propio venv-- pero comparte el checkout, asi que
# apunta al static del producto por ruta.
#
# Esta linea fue lo unico que el re-empaquetado rompio sin que ningun test
# lo viera (la suite no toca admin/): el proceso viejo seguia en memoria y
# la rotura recien habria aparecido en el proximo restart. Hay un test que
# ahora la vigila (tests/test_layout_paquete.py).
STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "web", "static"
)

app = create_admin_app(
    product_name="Contalibra",
    auth=auth, services=services, templates=templates,
    clientes_router=clientes_router.router,
    static_dir=STATIC_DIR,
)
