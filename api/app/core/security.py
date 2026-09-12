"""
Hashes, tokens y cookies.

Todo lo que firma o verifica una sesion pasa por aqui. Es el unico modulo con
logica de seguridad de la API, y por eso es el que mas comentarios lleva: cada
decision de aqui tiene una forma de salir mal que no da sintoma.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

MetodoDeAcceso = Literal["email", "pin"]

# Argon2id, no bcrypt: bcrypt trunca en 72 bytes y no tiene coste de memoria,
# que es lo que encarece un ataque con GPU.
_hasher = PasswordHash.recommended()

# Verificar contra esto cuando el usuario no existe. Sin ello, un correo
# registrado tarda ~100 ms (hay hash que comprobar) y uno inexistente tarda
# ~0 ms, asi que el tiempo de respuesta dice que cuentas existen.
_HASH_DE_DESCARTE = _hasher.hash("zentra-descarte-tiempo-constante")


def hashear(secreto: str) -> str:
    return _hasher.hash(secreto)


def verificar(secreto: str, hash_guardado: str | None) -> bool:
    if not hash_guardado:
        # Se gasta el mismo tiempo igualmente: ver arriba.
        _hasher.verify(secreto, _HASH_DE_DESCARTE)
        return False
    try:
        return _hasher.verify(secreto, hash_guardado)
    except Exception:
        # Un hash corrupto o de otro algoritmo es «no coincide», no un 500.
        return False


# --- tokens -----------------------------------------------------------------


def _ahora() -> datetime:
    return datetime.now(UTC)


def firmar_acceso(datos: dict[str, Any], metodo: MetodoDeAcceso) -> str:
    duracion = (
        timedelta(hours=settings.jwt_pin_access_hours)
        if metodo == "pin"
        else timedelta(minutes=settings.jwt_access_minutes)
    )
    emitido = _ahora()
    carga = {
        **datos,
        "login_method": metodo,
        "iat": emitido,
        "exp": emitido + duracion,
        # Aunque el acceso no se guarde en base, lleva jti: es lo que permitira
        # senalar un token concreto en un log sin escribir el token entero.
        "jti": str(uuid4()),
    }
    return jwt.encode(carga, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def firmar_refresco(user_id: UUID, metodo: MetodoDeAcceso) -> tuple[str, UUID, datetime]:
    """
    Devuelve (token, jti, caducidad).

    El `jti` no es decoracion. Sin el, dos inicios de sesion del mismo usuario en
    el MISMO SEGUNDO producen un JWT byte a byte identico —la carga es
    determinista y el `iat` va en segundos— y el segundo choca contra la clave
    de la tabla. Es un 500 en un caso que pasa de verdad: el operario que toca
    dos veces porque la primera no respondio.
    """
    duracion = (
        timedelta(hours=settings.jwt_pin_refresh_hours)
        if metodo == "pin"
        else timedelta(days=settings.jwt_refresh_days)
    )
    emitido = _ahora()
    caducidad = emitido + duracion
    jti = uuid4()
    token = jwt.encode(
        {
            "sub": str(user_id),
            "login_method": metodo,
            "jti": str(jti),
            "iat": emitido,
            "exp": caducidad,
        },
        settings.jwt_refresh_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, jti, caducidad


def leer_acceso(token: str) -> dict[str, Any]:
    """Lanza `jwt.PyJWTError` si no vale. Quien llama decide que 401 devolver."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def leer_refresco(token: str) -> dict[str, Any]:
    # Secreto DISTINTO del de acceso. Con el mismo, un token de acceso valdria
    # como token de refresco y la rotacion no significaria nada.
    return jwt.decode(token, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm])


# --- cookies ----------------------------------------------------------------

COOKIE_ACCESO = "access_token"
COOKIE_REFRESCO = "refresh_token"


def opciones_de_cookie() -> dict[str, Any]:
    """
    Los MISMOS atributos al poner y al borrar.

    Varios navegadores cotejan el conjunto de atributos para invalidar una
    cookie: si el borrado lleva un `secure` o un `samesite` distinto del que se
    uso al ponerla, la cookie SOBREVIVE al cierre de sesion. Por eso hay una
    sola funcion y la usan los dos caminos.

    `samesite=strict` funciona porque el navegador siempre habla con su propio
    origen: el servidor de Next reenvia `/api` a la API.
    """
    return {
        "httponly": True,
        "secure": not settings.is_dev,
        "samesite": "strict",
        "path": "/",
    }


# --- tickets de WebSocket ---------------------------------------------------

TICKET_SEGUNDOS = 30


def firmar_ticket(datos: dict[str, Any]) -> str:
    """
    Un pase de un solo viaje para abrir el WebSocket.

    POR QUE NO LA COOKIE. El `WebSocket` del navegador NO ADMITE CABECERAS, asi
    que la unica via seria la cookie del handshake — y la cookie es
    `samesite=strict`, que en desarrollo (web en :3000, API en :8000) no viaja.
    Habria un camino de autenticacion en desarrollo y otro en produccion, que es
    exactamente lo que no se quiere.

    Dura treinta segundos: lo justo para pedirlo y abrir el socket. Va en la URL,
    asi que puede acabar en un log de acceso; que caduque enseguida es lo que
    hace que eso no importe.
    """
    emitido = _ahora()
    return jwt.encode(
        {
            **datos,
            "typ": "ws_ticket",
            "iat": emitido,
            "exp": emitido + timedelta(seconds=TICKET_SEGUNDOS),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def leer_ticket(token: str) -> dict[str, Any]:
    carga = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if carga.get("typ") != "ws_ticket":
        # Un token de acceso NO vale como ticket. Sin esta comprobacion, el
        # token de sesion —que dura horas— serviria para abrir sockets, y
        # entonces el ticket no habria servido para nada.
        raise jwt.InvalidTokenError("El token no es un ticket de WebSocket")
    return carga
