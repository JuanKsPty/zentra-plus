"""
Cache del contador de revocacion.

Los permisos y la identidad viajan dentro del token para que el guard no tenga
que consultar la base en cada peticion — el tablero de cocina y el salon hacen
decenas por accion humana. El precio es que un cambio de permisos no surte
efecto hasta el siguiente token, y `token_version` es lo que arregla eso: si el
numero del token no cuadra con el del usuario, la sesion esta revocada.

Comprobarlo contra la base en cada peticion devolveria la consulta que veniamos
a evitar, asi que se cachea 30 segundos, y quien sube el contador invalida su
propia entrada al momento.
"""

import threading
import time
from uuid import UUID

from sqlmodel import Session, select

from app.models import User

TTL_SEGUNDOS = 30.0

_cache: dict[UUID, tuple[int, float]] = {}
_candado = threading.Lock()


def version_de(session: Session, user_id: UUID) -> int | None:
    """
    La version actual del usuario, o None si no se pudo averiguar.

    FALLA EN ABIERTO a proposito: si la base no responde se devuelve None y
    quien llama acepta el token. Esto es una caja registradora — un parpadeo de
    PostgreSQL no puede echar del sistema al salon entero a media hora punta. El
    riesgo que se acepta es que una sesion revocada siga viva unos segundos
    mientras la base esta caida, que es el menor de los dos males.
    """
    ahora = time.monotonic()

    with _candado:
        guardado = _cache.get(user_id)
        if guardado is not None and ahora - guardado[1] < TTL_SEGUNDOS:
            return guardado[0]

    try:
        version = session.exec(select(User.token_version).where(User.id == user_id)).first()
    except Exception:
        with _candado:
            anterior = _cache.get(user_id)
        return anterior[0] if anterior else None

    if version is None:
        return None

    with _candado:
        _cache[user_id] = (int(version), ahora)
    return int(version)


def invalidar(user_id: UUID) -> None:
    """Se llama al subir el contador, para que el cambio no espere 30 segundos."""
    with _candado:
        _cache.pop(user_id, None)


def vaciar() -> None:
    """Solo para las pruebas: el estado global entre casos es una trampa."""
    with _candado:
        _cache.clear()
