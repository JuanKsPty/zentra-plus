"""
El reemplazo del guard global de NestJS.

Alli, dos guards registrados en la aplicacion hacen que el default sea denegar y
olvidarse sea imposible por construccion. FastAPI no tiene ese gancho, asi que la
garantia se reconstruye en tres capas —la sesion exigida en el router padre,
`requiere()` por endpoint, y esto— y ESTA es la que cierra el circulo: si un
endpoint nuevo no declara nada, la suite se pone roja con su ruta en el mensaje.

Sin esta prueba, «que rutas estan desprotegidas» no tiene respuesta salvo leerlas
todas, y el fallo es invisible hasta que alguien lo explota.
"""

from collections.abc import Iterator
from typing import Any

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core import permissions as P
from app.core.deps import sesion_requerida
from app.main import app
from tests.factories import cookie_con

# Abiertas a proposito. Anadir algo aqui es una decision visible en un diff.
PUBLICAS = {
    ("GET", "/api/health"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/pin"),
    ("POST", "/api/auth/refresh"),
    # La rejilla del teclado de PIN: hay que verla ANTES de tener sesion, porque
    # es como se elige quien eres.
    ("GET", "/api/users/operational"),
    # Cerrar sesion NO exige sesion, y es deliberado: si la exigiera, quien
    # tiene el token de acceso caducado no podria cerrarla — justo cuando mas
    # falta hace. Lee la cookie de refresco, revoca ese refresco y borra las dos
    # cookies. Sin cookie no hace nada y responde 204 igual, porque el resultado
    # que el cliente pidio («no quiero seguir con la sesion») ya se cumple.
    ("POST", "/api/auth/logout"),
}

# Autenticadas pero sin permiso concreto: son recursos del propio usuario, y
# exigir un permiso para leer tu propia sesion no significaria nada.
SOLO_SESION = {
    ("GET", "/api/auth/me"),
}

# Las rutas que montan otros archivos de pruebas para ejercitar los manejadores.
PREFIJOS_DE_PRUEBA = ("/api/_pruebas",)


def _caminar(
    rutas: list[Any], prefijo: str = "", heredadas: tuple = ()
) -> Iterator[tuple[str, APIRoute, tuple]]:
    """
    Recorre los routers ANIDADOS.

    `include_router` de esta version de FastAPI no aplana: deja un router
    intermedio que envuelve al original, asi que `app.routes` solo ve el primer
    nivel. Leerlo sin bajar daria una lista vacia y esta prueba pasaria sin
    mirar nada — que es exactamente el modo de fallo que hay que evitar en un
    guardian.

    Las dependencias del router padre viajan en el contexto de inclusion y NO en
    la ruta, asi que se acumulan por separado: son las que llevan la exigencia
    de sesion.
    """
    for ruta in rutas:
        if isinstance(ruta, APIRoute):
            yield prefijo + ruta.path, ruta, heredadas
        elif hasattr(ruta, "original_router") and hasattr(ruta, "include_context"):
            contexto = ruta.include_context
            yield from _caminar(
                ruta.original_router.routes,
                prefijo + (contexto.prefix or ""),
                heredadas + tuple(contexto.dependencies),
            )


def _exige_sesion(ruta: APIRoute, heredadas: tuple) -> bool:
    """
    Si esta ruta acaba pasando por `sesion_requerida`, por la via que sea.

    Hay dos vias legitimas y las dos cuentan: heredarla del router padre —que es
    como se protege todo un modulo de golpe— o declararla en la propia firma,
    que es lo que hacen `/auth/me` y `/auth/logout`, porque viven en el router
    de sesion junto a los endpoints publicos de entrada y no pueden colgar del
    padre protegido.
    """
    if any(getattr(d, "dependency", None) is sesion_requerida for d in heredadas):
        return True

    # El arbol de la ruta: `requiere()` depende a su vez de la sesion, asi que
    # la referencia esta un nivel mas abajo.
    pendientes = list(ruta.dependant.dependencies)
    while pendientes:
        dependencia = pendientes.pop()
        if dependencia.call is sesion_requerida:
            return True
        pendientes.extend(dependencia.dependencies)
    return False


def _permisos_declarados(ruta: APIRoute) -> set[str]:
    declarados: set[str] = set()
    for dependencia in ruta.dependant.dependencies:
        declarados |= set(getattr(dependencia.call, "__permisos__", ()))
    return declarados


def _marcada_publica(ruta: APIRoute) -> bool:
    return any(getattr(d.call, "__publico__", False) is True for d in ruta.dependant.dependencies)


def _rutas() -> list[tuple[str, str, APIRoute, tuple]]:
    encontradas = []
    for path, ruta, heredadas in _caminar(app.routes):
        if path.startswith(PREFIJOS_DE_PRUEBA):
            continue
        for metodo in sorted(ruta.methods - {"HEAD", "OPTIONS"}):
            encontradas.append((metodo, path, ruta, heredadas))
    return encontradas


def test_toda_ruta_declara_su_permiso_o_esta_en_la_lista_blanca() -> None:
    huerfanas = []

    for metodo, path, ruta, _ in _rutas():
        clave = (metodo, path)
        if clave in PUBLICAS or clave in SOLO_SESION:
            continue
        if _marcada_publica(ruta):
            continue
        if not _permisos_declarados(ruta):
            huerfanas.append(f"{metodo} {path}")

    assert not huerfanas, (
        "Estos endpoints no exigen ningun permiso y no estan en la lista blanca:\n  "
        + "\n  ".join(huerfanas)
        + "\n\nAnade `dependencies=[Depends(requiere('modulo:accion'))]`, o incluyelo "
        "en PUBLICAS de este archivo explicando por que."
    )


def test_la_lista_blanca_no_se_queda_vieja() -> None:
    """
    Una lista blanca que nombra rutas que ya no existen deja de protegerse sola:
    nadie la revisa y acaba autorizando cosas que se llaman parecido.
    """
    existentes = {(metodo, path) for metodo, path, _, _ in _rutas()}
    fantasmas = (PUBLICAS | SOLO_SESION) - existentes

    assert not fantasmas, f"La lista blanca nombra rutas que ya no existen: {sorted(fantasmas)}"


def test_el_guardian_sabe_leer_los_permisos_de_una_ruta() -> None:
    """
    Si `__permisos__` dejara de propagarse, la prueba de arriba veria cero
    permisos en todas partes y fallaria — pero si cambiara al reves, veria
    permisos donde no los hay y pasaria sin mirar. Esto ancla que sabe leerlos.
    """
    por_ruta = {(metodo, path): _permisos_declarados(ruta) for metodo, path, ruta, _ in _rutas()}

    assert por_ruta[("GET", "/api/users")] == {P.USERS_READ}
    assert por_ruta[("GET", "/api/roles")] == {P.ROLES_READ}


def test_el_recorrido_encuentra_las_rutas() -> None:
    """
    El guardian tiene que poder fallar.

    `include_router` no aplana los routers en esta version de FastAPI: si el
    recorrido no bajara a los anidados, encontraria cero rutas, no habria
    huerfanas y la prueba de arriba pasaria siempre sin mirar nada.
    """
    rutas = {(metodo, path) for metodo, path, _, _ in _rutas()}

    assert ("GET", "/api/users") in rutas
    assert ("POST", "/api/auth/login") in rutas
    assert len(rutas) >= 8


def test_toda_ruta_no_publica_exige_sesion_desde_el_router_padre() -> None:
    """
    La primera de las tres capas.

    La sesion se exige en el router padre y no endpoint por endpoint, asi que un
    modulo nuevo no puede quedar abierto por olvidar una dependencia. Esto
    comprueba que la herencia de verdad llega, que es lo que no se ve leyendo
    el archivo del modulo.
    """
    sin_sesion = [
        f"{metodo} {path}"
        for metodo, path, ruta, heredadas in _rutas()
        if (metodo, path) not in PUBLICAS and not _exige_sesion(ruta, heredadas)
    ]

    assert not sin_sesion, "Estas rutas no cuelgan del router que exige sesion:\n  " + "\n  ".join(
        sin_sesion
    )


def test_las_rutas_publicas_NO_exigen_sesion() -> None:
    """
    El reverso. Si la rejilla del teclado de PIN acabara bajo el router
    protegido, la pantalla de acceso por PIN no podria pintarse — y el sintoma
    seria «no carga», no «falta un permiso».
    """
    publicas_con_sesion = [
        f"{metodo} {path}"
        for metodo, path, ruta, heredadas in _rutas()
        if (metodo, path) in PUBLICAS and _exige_sesion(ruta, heredadas)
    ]

    assert not publicas_con_sesion, (
        "Estas rutas deberian ser publicas pero exigen sesion:\n  "
        + "\n  ".join(publicas_con_sesion)
    )


# --- comportamiento ---------------------------------------------------------


def test_sin_sesion_es_401(client: TestClient) -> None:
    respuesta = client.get("/api/users")

    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "sin_sesion"


def test_con_sesion_pero_sin_el_permiso_es_403(client: TestClient) -> None:
    client.cookies.update(cookie_con([]))

    respuesta = client.get("/api/users")

    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "sin_permiso"


def test_un_permiso_PARECIDO_no_sirve(client: TestClient) -> None:
    """
    El caso que atrapa una comparacion por prefijo o un `in` mal escrito.

    `users:write` empieza igual que `users:read` hasta el tercer caracter del
    verbo, y una comprobacion perezosa los daria por equivalentes.
    """
    client.cookies.update(cookie_con([P.USERS_WRITE]))

    assert client.get("/api/users").status_code == 403


def test_con_el_permiso_correcto_pasa(client: TestClient) -> None:
    client.cookies.update(cookie_con([P.USERS_READ]))

    assert client.get("/api/users").status_code == 200


def test_el_error_403_no_dice_que_permiso_falta(client: TestClient) -> None:
    """Le diria a quien sondea el nombre exacto de lo que tiene que conseguir."""
    client.cookies.update(cookie_con([]))

    cuerpo = client.get("/api/users").text

    assert "users:read" not in cuerpo


def test_un_permiso_inventado_revienta_al_declararlo() -> None:
    """
    `requiere("orders:crate")` no puede convertirse en una puerta cerrada para
    siempre que nadie relaciona con un typo. Falla al importar el modulo.
    """
    import pytest

    from app.core.deps import requiere

    with pytest.raises(RuntimeError, match="Permiso desconocido"):
        requiere("orders:crate")
