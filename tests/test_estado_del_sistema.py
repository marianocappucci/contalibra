"""La barra de estado del pie (libracore ADR-075, libra-ui ADR-083): `GET /api/estado-del-sistema` está montada, pide
sesión y, para el administrador de una instancia común, trae el respaldo y nada de LibraEdge."""


def test_sin_sesion_no_contesta(client):
    assert client.get("/api/estado-del-sistema").status_code == 401


def test_el_admin_ve_usuario_respaldo_y_version(admin_client):
    r = admin_client.get("/api/estado-del-sistema")
    assert r.status_code == 200
    datos = r.json()
    assert datos["usuario"]["rol"] == "admin" and datos["usuario"]["nombre"]
    assert datos["libraedge"] is None, "fuera de un nodo y sin nodos registrados no hay nada de LibraEdge"
    assert datos["respaldo"] is not None and datos["respaldo"]["nivel"] in {"ok", "atencion"}
    assert datos["version"]["motor"]
    assert datos["refrescar_en_segundos"] == 300


def test_el_central_con_un_nodo_lo_cuenta_y_sin_noticias(admin_client, monkeypatch):
    """Un nodo registrado que todavía no sincronizó nunca es «sin noticias» para el central (sólo el admin lo ve)."""
    from libraedge.aprovisionamiento import registrar

    from app.db_core import get_connection
    from app.offline import aprovisionamiento

    # Sin contratar nada: LibraEdge está incluido en todos los planes (libraedge ADR-014).
    with get_connection() as conn:
        registrar(conn, aprovisionamiento, "nodo-ficticio", "Casa central", salida=lambda _: None)
    datos = admin_client.get("/api/estado-del-sistema").json()
    assert datos["libraedge"] == {"rol": "central", "nodos": 1, "sin_noticias": 1, "nivel": "atencion"}
