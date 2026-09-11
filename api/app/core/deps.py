"""
Las dependencias que atraviesan toda la API: sesion, base y sucursal.
"""

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Request
from pydantic import BaseModel
from sqlmodel import Session

from app.core import token_version
from app.core.errors import ErrorAplicacion
from app.core.security import COOKIE_ACCESO, MetodoDeAcceso, leer_acceso
from app.db.session import get_session

SessionDep = Annotated[Session, Depends(get_session)]


class Sesion(BaseModel):
    """Lo que la API sabe de quien esta pidiendo, leido del token."""

    sub: UUID
    tv: int = 0
    name: str
    email: str | None = None
    # La sucursal ACTIVA. Viaja dentro del token firmado y no en una cabecera ni
    # en la query: si viniera de fuera, operar en la sede de al lado seria
    # cuestion de cambiar un campo del JSON.
    branch_id: UUID
    branch_ids: list[UUID] = []
    login_method: MetodoDeAcceso = "email"
    permissions: list[str] = []


def _token_de(request: Request) -> str | None:
    """
    La cookie, y como alternativa la cabecera `Authorization`.

    La cookie es el camino normal, porque es httpOnly y no pasa por JavaScript.
    La cabecera se acepta para poder probar con curl y desde `/api/docs` sin
    montar un navegador.
    """
    if (cookie := request.cookies.get(COOKIE_ACCESO)) is not None:
        return cookie
    cabecera = request.headers.get("Authorization", "")
    if cabecera.lower().startswith("bearer "):
        return cabecera[7:].strip() or None
    return None


def sesion_requerida(request: Request, session: SessionDep) -> Sesion:
    token = _token_de(request)
    if token is None:
        raise ErrorAplicacion(401, "sin_sesion", "Hay que iniciar sesion.")

    try:
        carga = leer_acceso(token)
    except jwt.ExpiredSignatureError as error:
        # Mensaje distinto del de «token invalido» a proposito: el cliente
        # reintenta con el refresco solo ante este, y para la persona significa
        # «vuelve a entrar», no «algo va mal».
        raise ErrorAplicacion(401, "sesion_expirada", "La sesion expiro.") from error
    except jwt.PyJWTError as error:
        raise ErrorAplicacion(401, "token_invalido", "La sesion no es valida.") from error

    try:
        sesion = Sesion.model_validate(carga)
    except ValueError as error:
        raise ErrorAplicacion(401, "token_invalido", "La sesion no es valida.") from error

    actual = token_version.version_de(session, sesion.sub)
    # `actual is None` = no se pudo comprobar. Se acepta: ver token_version.py.
    if actual is not None and actual != sesion.tv:
        raise ErrorAplicacion(
            401,
            "sesion_revocada",
            "La sesion se cerro. Vuelve a iniciar sesion.",
        )

    return sesion


SesionActual = Annotated[Sesion, Depends(sesion_requerida)]
