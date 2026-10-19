"""La sucursal única «Casa central» (plan de sucursales, F1; ADR-063 de libracommerce).

Contalibra es de un solo local, pero el motor ya tiene sucursales. Esta revisión (`0006_sucursal_unica`) y `init_db()`
dejan los depósitos, las cajas y las ventas de antes bajo UNA sucursal predeterminada, para que el día que un cliente
pida multisucursal no haya que migrar datos. Lo que fija este archivo:

1. **Nada visible cambia.** Las rutas de siempre devuelven lo mismo con y sin la sucursal, salvo los campos de
   sucursal (`branch_id`, `sucursal_id`); `/api/sucursales` sigue sin existir; el kit no recibe nada que lo haga mostrar
   una sucursal.
2. Una instancia nueva nace con la sucursal; el depósito y la venta nuevos cuelgan de ella.
3. La revisión, en la cadena real (`alembic upgrade/downgrade`), con datos: upgrade -> downgrade -> upgrade.
4. El camino de vuelta sólo toca lo que es de la migración.

Corre contra PostgreSQL (fixture `client`/`admin_client`).
"""
import importlib
import os
import subprocess

import pytest
from libraauth.session_auth import PANEL_TOKEN_ENV

from app import database as db
from app import db_core
from app.sucursal_unica import NOMBRE, adoptar, desadoptar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVISION_ANTERIOR = "0005_branches_hora_ar"
REVISION = "0006_sucursal_unica"
CLAVES_DE_SUCURSAL = {"branch_id", "sucursal_id"}
TOKEN_DE_PANEL = "token-de-panel-de-la-suite"


# ── Helpers ──────────────────────────────────────────────────────────────


def _filas(sql, params=()):
    with db_core.get_connection() as conn:
        return [tuple(f) for f in conn.execute(sql, params).fetchall()]


def _sucursales():
    return _filas("SELECT id, name, is_default, default_location_id, active FROM branches ORDER BY id")


def _sucursal_unica() -> int:
    [(sid, nombre, es_default, _, activa)] = _sucursales()
    assert (nombre, es_default, activa) == (NOMBRE, 1, 1)
    return sid


def _quitar_claves(valor, claves=CLAVES_DE_SUCURSAL):
    """La respuesta sin los campos de sucursal: lo único que tiene permitido cambiar."""
    if isinstance(valor, dict):
        return {k: _quitar_claves(v, claves) for k, v in valor.items() if k not in claves}
    if isinstance(valor, list):
        return [_quitar_claves(v, claves) for v in valor]
    return valor


def _con_claves(valor, claves=CLAVES_DE_SUCURSAL):
    """Cuántas veces aparece alguno de los campos de sucursal y con qué valores (para el control positivo)."""
    if isinstance(valor, dict):
        return [v for k, v in valor.items() if k in claves] + [x for v in valor.values() for x in _con_claves(v, claves)]
    if isinstance(valor, list):
        return [x for v in valor for x in _con_claves(v, claves)]
    return []


def _post(client, ruta, **json):
    r = client.post(ruta, json=json)
    assert r.status_code == 200, f"{ruta}: {r.status_code} {r.text}"
    return r.json()


# ── Una instancia nueva nace con su sucursal ─────────────────────────────


def test_una_instancia_nueva_nace_con_casa_central(client):
    sid = _sucursal_unica()
    [(principal,)] = _filas("SELECT id FROM locations WHERE is_default = 1")
    assert _sucursales()[0][3] == principal                      # su depósito de venta es el principal
    assert _filas("SELECT DISTINCT branch_id FROM locations") == [(sid,)]
    assert _filas("SELECT DISTINCT sucursal_id FROM cajas") == [(sid,)]


def test_init_db_otra_vez_no_cambia_nada(client):
    antes = (_sucursales(), _filas("SELECT id, branch_id FROM locations ORDER BY id"),
             _filas("SELECT id, sucursal_id FROM cajas ORDER BY id"))
    db.init_db()
    db.init_db()
    assert antes == (_sucursales(), _filas("SELECT id, branch_id FROM locations ORDER BY id"),
                     _filas("SELECT id, sucursal_id FROM cajas ORDER BY id"))


def test_adoptar_informa_lo_que_hizo_y_la_segunda_no_hace_nada(client):
    with db_core.get_connection() as conn:
        conn.execute("DELETE FROM branches")
        conn.execute("UPDATE locations SET branch_id = NULL")
        conn.execute("UPDATE cajas SET sucursal_id = NULL")
        depositos = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
        cajas = conn.execute("SELECT COUNT(*) FROM cajas").fetchone()[0]
        primera = adoptar(conn)
        segunda = adoptar(conn)
    assert primera == {"sucursal_id": _sucursal_unica(), "sucursal_creada": True, "depositos_asignados": depositos,
                       "cajas_asignadas": cajas, "ventas_completadas": 0}
    assert segunda == {"sucursal_id": primera["sucursal_id"], "sucursal_creada": False, "depositos_asignados": 0,
                       "cajas_asignadas": 0, "ventas_completadas": 0}


def test_una_caja_que_ya_tiene_sucursal_no_se_toca(client):
    with db_core.get_connection() as conn:
        conn.execute("INSERT INTO cajas (nombre, descripcion, medios_pago, sucursal_id) VALUES ('Ajena', '', '[]', 987)")
        adoptar(conn)
    assert _filas("SELECT sucursal_id FROM cajas WHERE nombre = 'Ajena'") == [(987,)]


# ── El depósito y la venta nuevos cuelgan de la sucursal ─────────────────


def test_el_deposito_nuevo_cae_en_casa_central(admin_client):
    sid = _sucursal_unica()
    creado = _post(admin_client, "/api/depositos", nombre="Camioneta")
    assert creado["branch_id"] == sid
    assert _filas("SELECT DISTINCT branch_id FROM locations") == [(sid,)]
    assert _sucursales()[0][3] != creado["id"]                   # no le quita el depósito de venta al principal


def test_la_caja_nueva_cae_en_casa_central_y_una_explicita_se_respeta(admin_client):
    """Libracore ADR-062: la caja creada por la API sin `sucursal_id` nace en la predeterminada y no queda en NULL
    hasta el próximo arranque; con uno explícito se respeta; editarla no cambia su sucursal."""
    sid = _sucursal_unica()
    creada = _post(admin_client, "/api/cajas", nombre="Mostrador 2")
    assert creada["sucursal_id"] == sid
    assert _filas("SELECT sucursal_id FROM cajas WHERE id = ?", (creada["id"],)) == [(sid,)]
    explicita = _post(admin_client, "/api/cajas", nombre="Anexo", sucursal_id=987)
    assert explicita["sucursal_id"] == 987
    editada = admin_client.put(f"/api/cajas/{creada['id']}", json={"nombre": "Mostrador 3", "sucursal_id": 987})
    assert editada.status_code == 200 and editada.json()["sucursal_id"] == sid
    assert _filas("SELECT DISTINCT sucursal_id FROM cajas WHERE nombre <> 'Anexo'") == [(sid,)]


def test_la_caja_nueva_en_una_instancia_sin_sucursal_queda_sin_ella(admin_client):
    """Sin ninguna sucursal (una base que nunca adoptó) la caja nace como siempre: sin sucursal."""
    with db_core.get_connection() as conn:
        conn.execute("UPDATE cajas SET sucursal_id = NULL")
        conn.execute("UPDATE locations SET branch_id = NULL")
        conn.execute("DELETE FROM branches")
    assert _post(admin_client, "/api/cajas", nombre="Mostrador 2")["sucursal_id"] is None


def test_la_venta_anota_la_sucursal_con_y_sin_stock_y_con_o_sin_producto(admin_client):
    sid = _sucursal_unica()
    p = _post(admin_client, "/api/productos", nombre="Fideos", precio_venta=500.0, precio_costo=300.0)
    admin_client.post(f"/api/stock/{p['id']}/ajuste", json={"modo": "absoluto", "cantidad": 20})
    con_producto = _post(admin_client, "/api/ventas", fecha="2026-10-16",
                         items=[{"nombre": "Fideos", "qty": 1, "precio": 500.0, "producto_id": p["id"]}],
                         pagos=[{"medio": "efectivo", "monto": 500.0}])
    suelta = _post(admin_client, "/api/ventas", fecha="2026-10-16",
                   items=[{"nombre": "Envío", "qty": 1, "precio": 100.0}],
                   pagos=[{"medio": "efectivo", "monto": 100.0}])
    assert _filas("SELECT id, branch_id FROM sales ORDER BY id") == [(con_producto["id"], sid), (suelta["id"], sid)]


# ── Nada visible cambia ──────────────────────────────────────────────────


def test_no_se_expone_la_multisucursal(admin_client):
    """F2 no se expone hasta que un cliente la pida: ni la ruta de sucursales ni nada que el kit use para ofrecerlas."""
    assert admin_client.get("/api/sucursales").status_code == 404
    assert not [r for r in admin_client.get("/openapi.json").json().get("paths", {}) if "sucursal" in r]


@pytest.fixture
def escenario(admin_client, monkeypatch):
    """Una instancia con de todo un poco: depósitos, stock, transferencia, listas de precio con quiebres, ventas de
    varias formas, una caja más, un turno y el resumen del panel."""
    monkeypatch.setenv(PANEL_TOKEN_ENV, TOKEN_DE_PANEL)
    c = admin_client
    yerba = _post(c, "/api/productos", nombre="Yerba", precio_venta=100.0, precio_costo=60.0)
    fideos = _post(c, "/api/productos", nombre="Fideos", precio_venta=500.0, precio_costo=300.0)
    camioneta = _post(c, "/api/depositos", nombre="Camioneta")
    principal = next(d for d in c.get("/api/depositos").json() if d["id"] != camioneta["id"])
    for p in (yerba, fideos):
        c.post(f"/api/stock/{p['id']}/ajuste", json={"modo": "absoluto", "cantidad": 50})
    _post(c, "/api/depositos/transferir", producto_id=yerba["id"], origen_id=principal["id"],
          destino_id=camioneta["id"], cantidad=10)
    with db_core.get_connection() as conn:
        conn.execute("UPDATE modulos SET habilitado=1 WHERE modulo='mayorista'")        # los quiebres y /precio son del add-on
    lista = db.create_lista_precio("Mayorista")
    db.save_lista_precio_items(lista, {yerba["id"]: 90.0, fideos["id"]: 450.0})
    db.set_quiebres(lista, yerba["id"], [{"min_quantity": 10, "amount": 80}])
    _post(c, "/api/cajas", nombre="Caja 2")
    _post(c, "/api/turnos/abrir", monto_inicial=1000.0)
    _post(c, "/api/ventas", fecha="2026-10-16",
          items=[{"nombre": "Yerba", "qty": 2, "precio": 100.0, "producto_id": yerba["id"]}],
          pagos=[{"medio": "efectivo", "monto": 200.0}])
    _post(c, "/api/ventas", fecha="2026-10-16", items=[{"nombre": "Envío", "qty": 1, "precio": 50.0}],
          pagos=[{"medio": "efectivo", "monto": 50.0}])
    return {"yerba": yerba["id"], "fideos": fideos["id"], "lista": lista, "camioneta": camioneta["id"],
            "principal": principal["id"]}


def _fotografia(client, e) -> dict:
    """Lo que ve un cliente: las respuestas de las rutas que tocan depósitos, listas, cajas, ventas y el resumen."""
    rutas = [
        "/api/depositos", f"/api/depositos/{e['principal']}/stock", f"/api/depositos/{e['camioneta']}/stock",
        f"/api/depositos/stock-producto/{e['yerba']}", "/api/depositos/transferencias",
        "/api/productos", "/api/stock", f"/api/stock/{e['yerba']}",
        "/api/listas-precio", f"/api/listas-precio/{e['lista']}/items",
        f"/api/listas-precio/{e['lista']}/precio?producto_id={e['yerba']}&cantidad=1",
        f"/api/listas-precio/{e['lista']}/precio?producto_id={e['yerba']}&cantidad=10",
        "/api/cajas", "/api/turnos", "/api/ventas", "/api/ventas/medios-pago",
    ]
    foto = {}
    for ruta in rutas:
        r = client.get(ruta)
        assert r.status_code == 200, f"{ruta}: {r.status_code} {r.text}"
        foto[ruta] = r.json()
    foto["/api/ventas/1"] = client.get("/api/ventas/" + str(foto["/api/ventas"][-1]["id"])).json()
    resumen = client.get("/api/resumen", headers={"X-Panel-Auth": TOKEN_DE_PANEL})
    assert resumen.status_code == 200, resumen.text
    foto["/api/resumen"] = resumen.json()
    return foto


def _sin_lo_que_cambia_solo(foto: dict) -> dict:
    """Quita lo que cambia sin que sea de sucursal: la hora del resumen, si la trae."""
    foto = _quitar_claves(foto)
    foto["/api/resumen"] = {k: v for k, v in foto["/api/resumen"].items() if k not in {"generado_en", "generado", "hora"}}
    return foto


def test_las_rutas_de_siempre_devuelven_lo_mismo_con_y_sin_la_sucursal(admin_client, escenario):
    """Con la sucursal única puesta y con la base como estaba antes de la migración (`desadoptar`), cada ruta de
    depósitos, stock, listas de precio, cajas, turnos, ventas y resumen da lo mismo salvo `branch_id`/`sucursal_id`."""
    con = _fotografia(admin_client, escenario)

    # Control positivo: el escenario SÍ tiene los campos de sucursal con la sucursal puesta (si no, comparar sin ellos
    # no probaría nada) y los tiene vacíos sin ella.
    campos = _con_claves(con)
    assert campos and all(v is not None for v in campos[:1]), campos
    assert _sucursal_unica() in campos

    with db_core.get_connection() as conn:
        desadoptar(conn)
    assert _sucursales() == []
    sin = _fotografia(admin_client, escenario)
    assert _con_claves(sin) and all(v is None for v in _con_claves(sin)), "sin la sucursal los campos van en null"

    assert _sin_lo_que_cambia_solo(con) == _sin_lo_que_cambia_solo(sin)


def test_los_depositos_de_siempre_con_un_campo_de_sucursal_lleno(admin_client, escenario):
    depositos = admin_client.get("/api/depositos").json()
    assert {d["branch_id"] for d in depositos} == {_sucursal_unica()}
    # `branch_id` ya era una clave de cada depósito (en null): la pantalla de depósitos no se entera de ninguna nueva.
    assert {"id", "nombre", "branch_id"} <= set(depositos[0])


def test_desactivar_un_deposito_se_comporta_como_siempre(admin_client, escenario):
    """El depósito por defecto no se desactiva (como antes) y el otro sí; la sucursal no agrega rechazos nuevos."""
    por_defecto = next(d for d in admin_client.get("/api/depositos").json() if d["es_default"])
    r = admin_client.put(f"/api/depositos/{por_defecto['id']}",
                         json={"nombre": por_defecto["nombre"], "descripcion": "", "activo": False})
    assert r.status_code == 422 and "por defecto" in r.text
    otro = escenario["camioneta"]
    r = admin_client.put(f"/api/depositos/{otro}", json={"nombre": "Camioneta", "descripcion": "", "activo": False})
    assert r.status_code == 200 and r.json()["activo"] in (0, False)


# ── La revisión de Alembic, en la cadena real ────────────────────────────


def _comandos_de_la_cadena(hasta: str) -> list[list[str]]:
    """Los comandos que el producto DECLARA para el deploy, con el último (`alembic upgrade head`) cortado en `hasta`."""
    from libracore.provisioning import get_config

    importlib.reload(importlib.import_module("scripts.panel_admin"))
    declarados = [list(c) for c in get_config().migraciones]
    assert declarados, "el producto no declara `migraciones`"
    final = declarados[-1]
    assert final[:3] == ["alembic", "upgrade", "head"], f"el deploy ya no termina en `alembic upgrade head`: {final}"
    return declarados[:-1] + [["alembic", "upgrade", hasta]]


def _correr(comando: list[str]) -> None:
    r = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True, env=os.environ.copy())
    assert r.returncode == 0, f"falló `{' '.join(comando)}`:\n{(r.stderr or r.stdout)[-2500:]}"


def _version() -> list[str]:
    return [f[0] for f in _filas("SELECT version_num FROM alembic_version_contalibra")]


def _estado() -> dict:
    return {
        "depositos": _filas("SELECT id, name, active, is_default, branch_id FROM locations ORDER BY id"),
        "cajas": _filas("SELECT id, nombre, sucursal_id FROM cajas ORDER BY id"),
        "ventas": _filas("SELECT id, number, branch_id FROM sales ORDER BY id"),
        "sucursales": _filas("SELECT name, is_default, default_location_id, active FROM branches ORDER BY id"),
    }


def _sembrar_una_instancia_de_antes() -> dict:
    """Los datos de una instancia que todavía no tiene sucursal: dos depósitos activos (uno por defecto) y uno inactivo,
    cajas (una ya con una sucursal ajena), y ventas con y sin depósito."""
    from libracommerce.erp import catalogo, ventas

    with db_core.get_connection() as conn:
        conn.execute("INSERT INTO locations (name, description, is_default, active) VALUES ('Depósito principal', '', 1, 1)")
        conn.execute("INSERT INTO locations (name, description, is_default, active) VALUES ('Camioneta', '', 0, 1)")
        conn.execute("INSERT INTO locations (name, description, is_default, active) VALUES ('Viejo', '', 0, 0)")
        conn.execute("INSERT INTO cajas (nombre, descripcion, medios_pago) VALUES ('Caja 2', '', '[]')")
        conn.execute("INSERT INTO cajas (nombre, descripcion, medios_pago, sucursal_id) VALUES ('Ajena', '', '[]', 987)")
        principal, camioneta, viejo = (f[0] for f in conn.execute("SELECT id FROM locations ORDER BY id").fetchall())
        pid = catalogo.create_producto(conn, "Yerba", precio_venta=100.0, precio_costo=60.0)
        kw = dict(fecha="2026-10-01", items=[{"nombre": "Yerba", "qty": 1, "precio": 100.0, "subtotal": 100.0,
                                              "producto_id": pid}], subtotal=100.0, descuento=0.0, total=100.0,
                  cliente_id=None, cliente_nombre="", usuario_id=None)
        v_principal = ventas.crear_venta(conn, numero="V-00001", **kw)
        v_camioneta = ventas.crear_venta(conn, numero="V-00002", **kw)
        v_inactivo = ventas.crear_venta(conn, numero="V-00003", **kw)
        v_sin_stock = ventas.crear_venta(conn, numero="V-00004", **kw)          # no movió stock: sin depósito
        for venta, deposito in ((v_principal, principal), (v_camioneta, camioneta), (v_inactivo, viejo)):
            conn.execute(
                "INSERT INTO stock_movements (item_id, location_id, movement_type, quantity_delta, occurred_at, "
                "source_type, source_id) VALUES (?, ?, 'sale', -1, '2026-10-01', 'venta', ?)", (pid, deposito, venta))
    return {"principal": principal, "camioneta": camioneta, "viejo": viejo, "ventas": (v_principal, v_camioneta,
            v_inactivo, v_sin_stock)}


def test_la_revision_en_la_cadena_con_datos_sube_baja_y_vuelve_a_subir(client):
    from tests.conftest import _reset_data_dir

    _reset_data_dir()                                                   # base vacía: la cadena arranca de cero
    for comando in _comandos_de_la_cadena(REVISION_ANTERIOR):
        _correr(comando)
    assert _version() == [REVISION_ANTERIOR]
    siembra = _sembrar_una_instancia_de_antes()
    antes = _estado()
    assert antes["sucursales"] == [] and {d[4] for d in antes["depositos"]} == {None}      # base de antes: sin sucursal

    # ── subir ── (hasta esta revisión y no `head`: la `0007_libraedge` de arriba no se baja, y bajar es parte del test)
    _correr(["alembic", "upgrade", REVISION])
    assert _version() == [REVISION]
    sid = _sucursal_unica()
    despues = _estado()
    assert despues["sucursales"] == [(NOMBRE, 1, siembra["principal"], 1)]
    assert {d[4] for d in despues["depositos"]} == {sid}                                   # también el inactivo
    assert dict((c[1], c[2]) for c in despues["cajas"]) == {**{c[1]: sid for c in antes["cajas"] if c[1] != "Ajena"},
                                                              "Ajena": 987}                # la ajena no se toca
    v_principal, v_camioneta, v_inactivo, v_sin_stock = siembra["ventas"]
    assert {v[0]: v[2] for v in despues["ventas"]} == {v_principal: sid, v_camioneta: sid, v_inactivo: sid,
                                                       v_sin_stock: None}                  # sin depósito: queda en NULL
    primera = _quitar_claves({k: v for k, v in despues.items()}, claves=set())

    # ── subir otra vez no hace nada ──
    _correr(["alembic", "upgrade", REVISION])
    assert _estado() == despues

    # ── bajar: queda como estaba antes, sin tocar lo ajeno ──
    _correr(["alembic", "downgrade", REVISION_ANTERIOR])
    assert _version() == [REVISION_ANTERIOR]
    assert _estado() == antes

    # ── y volver a subir: lo mismo que la primera vez (la sucursal se crea de nuevo) ──
    _correr(["alembic", "upgrade", REVISION])
    assert _version() == [REVISION]
    nuevo = _sucursal_unica()
    reasignado = _estado()
    assert reasignado["sucursales"] == primera["sucursales"] and reasignado["depositos"] == [
        (*d[:4], nuevo) for d in primera["depositos"]]
    assert [v[2] for v in reasignado["ventas"]] == [nuevo, nuevo, nuevo, None]


def test_una_instancia_que_nace_de_la_cadena_y_despues_arranca_queda_con_su_sucursal(client):
    """El alta: la cadena corre ANTES del primer arranque (base sin depósitos), y `init_db` siembra el depósito
    principal y lo cuelga de la sucursal que la revisión ya creó."""
    from tests.conftest import _reset_data_dir

    _reset_data_dir()
    for comando in _comandos_de_la_cadena("head"):
        _correr(comando)
    sid = _sucursal_unica()
    assert _filas("SELECT COUNT(*) FROM locations") == [(0,)]
    assert _sucursales()[0][3] is None                       # todavía sin depósito de venta

    db.init_db()
    assert _sucursal_unica() == sid
    assert _filas("SELECT name, branch_id FROM locations") == [("Depósito principal", sid)]
    [(principal,)] = _filas("SELECT id FROM locations")
    assert _sucursales()[0][3] == principal


# ── El camino de vuelta sólo toca lo que es de la migración ──────────────


def test_desadoptar_sin_sucursales_no_hace_nada(client):
    with db_core.get_connection() as conn:
        conn.execute("DELETE FROM branches")
        assert desadoptar(conn) == {"sucursal_id": None, "depositos": 0, "cajas": 0, "ventas": 0}


def test_desadoptar_se_niega_si_hay_mas_de_una_sucursal(client):
    from libracommerce.erp import catalogo

    with db_core.get_connection() as conn:
        catalogo.create_sucursal(conn, "Norte")
        antes = _estado()
        with pytest.raises(RuntimeError, match="más sucursales|sólo «Casa central»"):
            desadoptar(conn)
        assert _estado() == antes


def test_desadoptar_se_niega_si_la_unica_fue_renombrada(client):
    with db_core.get_connection() as conn:
        conn.execute("UPDATE branches SET name = 'Sede Centro'")
        with pytest.raises(RuntimeError, match="renombrada"):
            desadoptar(conn)
    assert _filas("SELECT name FROM branches") == [("Sede Centro",)]


@pytest.mark.parametrize("tabla", ["item_prices", "purchase_orders"])
def test_desadoptar_se_niega_si_un_precio_o_una_orden_apuntan_a_la_sucursal(client, tabla):
    from libracommerce.erp import catalogo

    sid = _sucursal_unica()
    with db_core.get_connection() as conn:
        if tabla == "item_prices":
            pid = catalogo.create_producto(conn, "Yerba", precio_venta=100.0)
            lista = db.create_lista_precio("Con sucursal")
            conn.execute("INSERT INTO item_prices (item_id, price_list_id, amount, valid_from, branch_id) "
                         "VALUES (?, ?, 90, '2026-01-01', ?)", (pid, lista, sid))
        else:
            [(party,)] = conn.execute(
                "INSERT INTO parties (party_type, display_name) VALUES ('supplier', 'Proveedor') RETURNING id"
            ).fetchall()
            conn.execute("INSERT INTO purchase_orders (number, supplier_party_id, branch_id) VALUES ('OC-1', ?, ?)",
                         (party, sid))
        with pytest.raises(RuntimeError, match=tabla):
            desadoptar(conn)
    assert _sucursal_unica() == sid
