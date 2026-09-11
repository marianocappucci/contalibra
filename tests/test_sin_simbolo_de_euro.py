"""Ningún `€` en lo que Contalibra le muestra al usuario.

Es la mitad que faltaba del *"Pendiente COMPROMETIDO — símbolo monetario"* del
2026-08-20. Se cerró el 2026-09-10 con una medición —0 ocurrencias en `main`—,
pero el pendiente pedía además **un test que falle si vuelve a aparecer**, y
una medición de un día no avisa de nada el día siguiente.

Se barren los fuentes del backend (`app/`) y del frontend (`frontend/src/`). Lo
que llega de `libra-ui` no está en este repo: lo cubre el paso del CI que busca
el `€` en el bundle compilado (`frontend/dist`), que es exactamente lo que se
sirve. Los PDF los arma `libracore.pdf_generator`, que ya reemplaza el `€` por
`EUR` y tiene sus tests en el motor.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

#: Se barren los directorios y no una lista de archivos escrita a mano: una
#: pantalla nueva tiene que entrar sola.
_DIRECTORIOS = ("app", "frontend/src")
_EXTENSIONES = {".py", ".html", ".jinja", ".j2", ".ts", ".tsx", ".js", ".jsx", ".css", ".json"}
_EXCLUIR = ("__pycache__", "/tests/", "/__tests__/", ".test.", ".spec.", "node_modules")


def _fuentes():
    for sub in _DIRECTORIOS:
        for archivo in sorted((RAIZ / sub).rglob("*")):
            if not archivo.is_file() or archivo.suffix not in _EXTENSIONES:
                continue
            if any(x in archivo.as_posix() for x in _EXCLUIR):
                continue
            yield archivo


def _texto(archivo: Path) -> str:
    return archivo.read_text(encoding="utf-8", errors="replace")


def test_el_barrido_lee_los_fuentes():
    """Control: sin esto, "no hay ningún €" pasaría también sobre un barrido que
    no leyó nada —porque el frontend se movió de carpeta, por ejemplo—.

    Y no alcanza con contar archivos: se exige que el signo de pesos **sí**
    aparezca, que es la otra cara de la misma propiedad.
    """
    fuentes = list(_fuentes())
    assert len(fuentes) > 50, f"el barrido encontró sólo {len(fuentes)} archivos"
    assert any(f.suffix == ".tsx" for f in fuentes), "no leyó el frontend"
    assert any("$" in _texto(f) for f in fuentes), "ningún archivo tiene un $"


def test_ningun_simbolo_de_euro_en_los_fuentes():
    hallados = [
        f"{archivo.relative_to(RAIZ).as_posix()}:{n}"
        for archivo in _fuentes()
        for n, linea in enumerate(_texto(archivo).splitlines(), 1)
        if "€" in linea
    ]
    assert not hallados, (
        "Contalibra muestra importes en pesos argentinos: un € en la interfaz o "
        f"en un comprobante es un error. Aparece en: {hallados}"
    )
