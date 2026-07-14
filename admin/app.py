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

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "static")

app = create_admin_app(
    product_name="Contalibra",
    auth=auth, services=services, templates=templates,
    clientes_router=clientes_router.router,
    static_dir=STATIC_DIR,
)
