"""
Definición única de los planes comerciales de Contalibra y qué módulos habilita
cada uno. Fuente de verdad compartida entre:

- `database.apply_plan()` (aplica el plan dentro de la instancia de un cliente).
- El backoffice `admin/` (asigna / sube / baja el plan de cada cliente).

Las claves de módulo deben coincidir con las de la tabla `modulos` (ver el seed
`_MODULOS_DEFAULT` en database.py). El módulo `turnos` no está gateado: siempre activo.
"""

PLANES = ["basico", "estandar", "premium"]

PLAN_LABELS = {
    "basico":   "Básico",
    "estandar": "Estándar",
    "premium":  "Premium",
}

# Precio mensual de referencia (informativo, para mostrar en el backoffice).
PLAN_PRECIOS = {
    "basico":   29000,
    "estandar": 59000,
    "premium":  89000,
}

# Módulos base del plan Básico.
_BASICO = {
    "clientes", "caja", "cajas", "ventas",
}

# Estándar = Básico + gestión completa (facturación, comprobantes, finanzas).
_ESTANDAR = _BASICO | {
    "facturacion", "remitos", "presupuestos", "productos", "listas_precio",
    "cuenta_corriente", "egresos", "proveedores", "tesoreria", "libros_iva", "reportes",
}

# Premium = Estándar + inventario y múltiples depósitos.
_PREMIUM = _ESTANDAR | {
    "stock", "depositos",
}

PLAN_MODULOS = {
    "basico":   set(_BASICO),
    "estandar": set(_ESTANDAR),
    "premium":  set(_PREMIUM),
}


def modulos_de_plan(plan: str) -> set[str]:
    """Devuelve el set de módulos habilitados para un plan (vacío si el plan es desconocido)."""
    return set(PLAN_MODULOS.get(plan, set()))


# Superset de todos los módulos gateables = los del plan más alto (Premium).
TODOS_LOS_MODULOS = set(PLAN_MODULOS["premium"])

# Add-ons opcionales: módulos pagos que se habilitan por instancia y NO
# pertenecen a ningún plan. No entran en `PLAN_MODULOS` ni en
# `TODOS_LOS_MODULOS`, así que ni `apply_plan` (motor) ni `aplicar_plan_en_db`
# (acá) los tocan al aplicar un plan — un add-on prendido sobrevive a subir o
# bajar de plan, que es justo lo que se paga. `libracore.db.modulos.apply_plan`
# lee este set con `getattr(plans, "ADDONS", set())`.
#   - mayorista: lista de precios por cliente + quiebres por cantidad
#     (paquete mayorista, ver wiki/analyses/distribuidora-mayorista-producto-candidato).
ADDONS = {"mayorista"}


def aplicar_plan_en_db(db_path: str, plan: str):
    """Aplica un plan escribiendo el estado de módulos directo en la DB SQLite de un
    cliente (`clientes/<slug>/data/contalibra.db`). Lo usa el backoffice para asignar /
    subir / bajar el plan de una instancia sin depender del contenedor.

    Es idempotente y crea las filas de módulos que falten (INSERT OR IGNORE + UPDATE),
    así que funciona igual sobre una DB recién seedeada o una existente. Requiere que la
    tabla `modulos` ya exista (la crea la app al iniciar).
    """
    import sqlite3
    if plan not in PLAN_MODULOS:
        raise ValueError(f"Plan desconocido: {plan!r}")
    activos = modulos_de_plan(plan)
    con = sqlite3.connect(db_path)
    try:
        # `- ADDONS`: aplicar un plan nunca toca un add-on. Hoy es equivalente a
        # iterar TODOS_LOS_MODULOS (los add-ons ya están afuera), pero deja la
        # invariante escrita: si alguien metiera un add-on en un set de plan por
        # error, seguiría sin gatearse por plan.
        for m in sorted(TODOS_LOS_MODULOS - ADDONS):
            on = 1 if m in activos else 0
            con.execute(
                "INSERT OR IGNORE INTO modulos (modulo, habilitado, plan) VALUES (?,?,?)",
                (m, on, plan),
            )
            con.execute(
                "UPDATE modulos SET habilitado=?, plan=? WHERE modulo=?",
                (on, plan, m),
            )
        con.commit()
    finally:
        con.close()
