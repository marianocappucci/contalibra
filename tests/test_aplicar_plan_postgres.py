"""`aplicar_plan_en_db` gatea los módulos en PostgreSQL, no en un SQLite muerto.

Regresión verificada en el VPS el 2026-09-03: `aplicar_plan_en_db` hacía
`sqlite3.connect(db_path)`, y contra la URL de PostgreSQL —el motor real de este
producto— fallaba con *"unable to open database file"*. O sea que el `set_plan`
del backoffice (y el alta) no aplicaban el plan: los módulos quedaban como los
dejó el seed (todos prendidos), sin gateo por plan. Ahora delega en
`apply_plan_modules`, que abre PostgreSQL.
"""
import pytest

import plans
from app import database as db
from app import db_core


def test_aplicar_plan_gatea_en_postgres_y_respeta_el_addon(client):
    assert db_core.ES_POSTGRES, "este test tiene sentido contra PostgreSQL"
    url = db_core.DB_PATH  # la URL de PostgreSQL de esta instancia

    # El add-on arranca apagado; se prende para verificar que el plan NO lo toca.
    with db.get_connection() as conn:
        conn.execute("UPDATE modulos SET habilitado=1 WHERE modulo=?", ("mayorista",))

    plans.aplicar_plan_en_db(url, "basico")

    mods = db.get_modulos()
    # Módulos del plan básico: prendidos.
    assert mods["ventas"] is True
    assert mods["caja"] is True
    # Módulos de planes superiores: apagados por el plan (esto es lo que antes NO
    # pasaba contra PostgreSQL).
    assert mods["facturacion"] is False   # estándar
    assert mods["stock"] is False         # premium
    assert mods["depositos"] is False     # premium
    # El add-on no pertenece a ningún plan: queda intacto.
    assert mods["mayorista"] is True


def test_subir_de_plan_reactiva_los_modulos(client):
    url = db_core.DB_PATH
    plans.aplicar_plan_en_db(url, "basico")
    assert db.get_modulos()["stock"] is False
    plans.aplicar_plan_en_db(url, "premium")
    assert db.get_modulos()["stock"] is True


def test_plan_desconocido_lanza(client):
    with pytest.raises(ValueError):
        plans.aplicar_plan_en_db(db_core.DB_PATH, "plan-inexistente")
