"""
Shim de compatibilidad: la infraestructura compartida (conexión SQLite,
utilidades de fecha/hora) vive ahora en `libracore.db.core`. Este archivo
solo configura la conexión con los parámetros de Contalibra y re-exporta
los mismos nombres que usaban los ~200 call sites existentes — ninguno
cambia una línea (Fase 3 de LibraCore, migración real a libracore.db, ver
wiki/entities/libracore.md).
"""
import os

from libracore.db import core as _lc_core

_DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(__file__))

# `CONTALIBRA_DATABASE_URL` gana sobre la ruta derivada de DATA_DIR. Es como
# este producto puede correr contra PostgreSQL: `libracore.db.core.configure()`
# acepta una URL desde `v1.16.0` y decide el backend por el destino, asi que
# aca no hay que elegir motor — solo dejar de imponer una ruta.
#
# Sin esto el motor quedaba fijado en la linea mas baja de la pila y no habia
# variable que poner: el mismo tope que tenia VentaLibra antes de su F3.
DB_PATH = os.environ.get("CONTALIBRA_DATABASE_URL") or os.path.join(
    _DATA_DIR, "contalibra.db"
)

# 🔴 **Este producto corre sobre PostgreSQL y nada mas.** La guarda va aca, en
# el arranque del producto, y no dentro de `libracore.db.core`: el motor tiene
# que poder abrir un SQLite igual, porque de eso vive la herramienta de
# diagnostico `python -m libracore.db.schema_dump`, que vuelca el schema de un
# archivo viejo o de la base de LibraEdge --- la excepcion permanente de la
# familia. La regla "este producto no habla con otro motor" es del producto.
#
# El modo SQLite se retiro el 2026-08-12: no chequea las FK, tipa dinamicamente
# y acepta cadenas donde la base pide enteros, asi que los defectos que
# PostgreSQL rechaza de entrada llegaban a produccion.
#
# Salta al IMPORTAR, no al primer query: si el destino esta mal, el arranque
# tiene que morir ahi y no a la mitad de la primera pantalla.
if not _lc_core.es_url_postgres(DB_PATH):
    raise RuntimeError(
        f"Contalibra corre solo sobre PostgreSQL y DB_PATH quedo en {DB_PATH!r}, que es "
        "una ruta de archivo. Defini CONTALIBRA_DATABASE_URL con la URL de "
        "la base."
    )

_lc_core.configure(db_path=DB_PATH)

#: Si el destino es PostgreSQL. Lo consultan `db_usuarios` —que arma su propio
#: engine de SQLAlchemy— y la suite, para no repetir el criterio en tres lados.
ES_POSTGRES = _lc_core.es_url_postgres(DB_PATH)

_AR_TZ = _lc_core._AR_TZ
_ar_now = _lc_core._ar_now
minutos_desde = _lc_core.minutos_desde
get_connection = _lc_core.get_connection
