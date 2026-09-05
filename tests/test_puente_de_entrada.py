"""La instancia de dev puede aceptar llamadas de otro producto de la familia.

🔴 **El defecto que esto cierra es silencioso, y por eso hace falta un test.**
Sin `LIBRA_SERVICE_TOKEN` declarada en el entorno, `token_de_servicio_valido`
devuelve `False` **sin mirar el header**: los endpoints que aceptan "admin o
servicio" se comportan como si sólo aceptaran admin.

Del otro lado eso se ve como un **401**, o sea igual que un token equivocado. El
emisor —[[medlibra]], mandando la consulta que acaba de cerrar— no tiene forma
de distinguir "me rechazaron la credencial" de "esta instancia ni siquiera mira
credenciales de servicio". Se pierde tiempo rotando un token que estaba bien.

🔑 **El default queda VACÍO a propósito**, y eso también se fija acá: un valor
real en el repo le daría acceso de servicio a cualquiera que lo lea, y
`dev.contalibra.com.ar` es público. El valor vive en el `.env` del VPS.
"""

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]
COMPOSE = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")

#: El servicio de la app en el compose de este repo. El de las instancias de
#: cliente lo genera el provisioning y vive en `clientes/<slug>/`.
SERVICIO_DEV = "contalibra-dev"


def test_el_compose_de_dev_declara_el_token_de_servicio():
    """Sin la declaración, el puente falla con 401 y parece un token mal
    copiado."""
    assert "- LIBRA_SERVICE_TOKEN=" in COMPOSE, (
        "el compose de dev no declara `LIBRA_SERVICE_TOKEN`: las llamadas de "
        "servicio se rechazan sin mirar el header"
    )


def test_el_default_del_token_esta_VACIO():
    """🔴 Un default con valor real sería una credencial publicada. Este repo es
    público y `dev.contalibra.com.ar` también."""
    m = re.search(r"- LIBRA_SERVICE_TOKEN=\$\{LIBRA_SERVICE_TOKEN:-([^}]*)\}", COMPOSE)
    assert m, "la declaración no usa la forma `${LIBRA_SERVICE_TOKEN:-...}`"
    assert m.group(1) == "", (
        f"el default del token de servicio no está vacío: «{m.group(1)}». "
        "Eso es una credencial en el repositorio."
    )


def test_el_control_del_patron_encuentra_un_default_con_valor():
    """🔑 El control positivo del test de arriba: pasa leyendo texto, así que
    con el patrón mal escrito daría verde para siempre sin mirar nada.

    Se le da una línea que **sí** tiene un default con valor y se comprueba que
    la reconoce — la de `ADMIN_USER`, que existe en este mismo archivo. Hasta
    F0 (2026-09-05) el control era `SECRET_KEY`, pero ese default se retiró a
    propósito (un secreto no lleva default en un repo público) y el control se
    quedó sin qué reconocer: por eso el control usa un default que NO es secreto.
    """
    m = re.search(r"- ADMIN_USER=\$\{ADMIN_USER:-([^}]*)\}", COMPOSE)
    assert m, "no se encontró `ADMIN_USER` para usar de control"
    assert m.group(1) != "", (
        "el control esperaba que `ADMIN_USER` tuviera un default con valor; "
        "si dejó de tenerlo, este control ya no distingue nada"
    )


def test_la_variable_del_OTRO_lado_no_esta_en_este_repo():
    """⚠️ Son dos permisos distintos y no se deben confundir.

    `CONTALIBRA_SERVICE_TOKEN` es el nombre que usa **MedLibra** para el token
    que nosotros le dejamos usar; `LIBRA_SERVICE_TOKEN` es el que **nosotros**
    aceptamos. Declarar el de ellos acá haría que rotar uno rote el otro sin que
    nadie lo pida.
    """
    #: ⚠️ Se busca la DECLARACIÓN (`- VAR=`), no el nombre suelto. La primera
    #: versión prohibía el string en cualquier parte y se puso roja con **el
    #: comentario de al lado**, que nombra la variable justamente para explicar
    #: por qué son dos. Un test que prohíbe hablar de algo no es lo mismo que
    #: uno que prohíbe declararlo.
    declaraciones = re.findall(r"^\s*-\s*CONTALIBRA_SERVICE_TOKEN=", COMPOSE, re.M)
    assert not declaraciones, (
        "el compose DECLARA la variable del emisor: son dos permisos distintos"
    )


def test_el_servicio_de_dev_sigue_siendo_el_que_se_cree():
    """Los tests de arriba miran el archivo entero. Si el servicio se renombrara
    —o el compose pasara a tener varios—, habría que revisarlos: este test es lo
    que hace que ese cambio no pase inadvertido."""
    assert f"container_name: {SERVICIO_DEV}" in COMPOSE
