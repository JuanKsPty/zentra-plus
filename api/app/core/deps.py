"""
Las dependencias que atraviesan toda la API: sesion, permisos y sucursal.
"""

import logging
from collections.abc import Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Query, Request
from pydantic import BaseModel
from sqlmodel import Session

from app.core import permissions, token_version
from app.core.errors import ErrorAplicacion
from app.core.security import COOKIE_ACCESO, MetodoDeAcceso, leer_acceso
from app.db.scoping import Alcance
from app.db.session import get_session

logger = logging.getLogger("zentra.auth")

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
    role_name: str | None = None
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


# --- autorizacion -----------------------------------------------------------
#
# NestJS consigue el «negar por defecto» con dos guards globales, y ahi olvidarse
# es imposible por construccion. FastAPI no tiene ese gancho, asi que la garantia
# se reconstruye en tres capas:
#
#   1. La sesion se exige en el ROUTER PADRE, no endpoint por endpoint. Los
#      publicos se enumeran uno a uno y con nombre en api/router.py.
#   2. `requiere(...)` declara el permiso de cada endpoint.
#   3. Una prueba recorre app.routes y falla si alguno no declara ninguno de los
#      dos. Ese test es el reemplazo real del guard global: hace que el olvido
#      sea imposible en vez de improbable.


def requiere(*permisos: str) -> Callable[..., None]:
    """
    Exige TODOS los permisos indicados.

    Se pone en el `dependencies=[]` del decorador y no como parametro de la
    funcion, para que no ensucie ni la firma ni el esquema de OpenAPI.

        @router.get("", dependencies=[Depends(requiere(P.ORDERS_READ))])

    El nombre se valida AL IMPORTAR: `requiere("orders:crate")` revienta el
    arranque en vez de convertirse en una puerta cerrada para siempre que nadie
    relaciona con un typo.
    """
    for permiso in permisos:
        if permiso not in permissions.CONOCIDOS:
            raise RuntimeError(
                f"Permiso desconocido: {permiso!r}. "
                f"Anadelo a app/core/permissions.py o corrige el nombre."
            )

    def comprobar(sesion: SesionActual) -> None:
        faltan = [p for p in permisos if p not in sesion.permissions]
        if faltan:
            logger.info("sin permiso: usuario %s, faltan %s", sesion.sub, ", ".join(faltan))
            # Lo que falta NO viaja en la respuesta: le diria a quien sondea el
            # nombre exacto del permiso que le falta. Al log, si.
            raise ErrorAplicacion(403, "sin_permiso", "No tienes permiso para hacer esto.")

    # Lo lee la prueba de cobertura para saber que exige cada ruta.
    comprobar.__permisos__ = permisos  # type: ignore[attr-defined]
    return comprobar


def publico() -> None:
    """
    Marca una ruta como abierta a proposito.

    No hace nada en tiempo de ejecucion: existe para que la prueba de cobertura
    distinga «abierto porque asi se decidio» de «abierto porque alguien se
    olvido». Sin esta marca, las dos cosas se ven igual en el codigo.
    """


publico.__publico__ = True  # type: ignore[attr-defined]


# --- alcance por sucursal ---------------------------------------------------


def sucursal_activa(
    sesion: SesionActual,
    branch: Annotated[
        str | None,
        Query(description="uuid de una sucursal, o 'all' para el consolidado"),
    ] = None,
) -> Alcance:
    """
    Sobre que sucursales opera esta peticion.

    Sin `?branch`, la del token. `?branch=all` da el consolidado y exige su
    propio permiso. Pedir una sucursal a la que la sesion no alcanza devuelve
    404 y no 403: un 403 confirmaria que esa sucursal existe.
    """
    alcanzables = tuple(sesion.branch_ids) or (sesion.branch_id,)

    if branch is None:
        return Alcance(branch_id=sesion.branch_id, branch_ids=alcanzables)

    if branch == "all":
        if permissions.BRANCHES_READ_ALL not in sesion.permissions:
            raise ErrorAplicacion(403, "sin_permiso", "No puedes consultar todas las sucursales.")
        return Alcance(branch_id=None, branch_ids=alcanzables)

    try:
        destino = UUID(branch)
    except ValueError as error:
        raise ErrorAplicacion(404, "no_encontrado", "Sucursal no encontrada.") from error

    if destino not in alcanzables:
        raise ErrorAplicacion(404, "no_encontrado", "Sucursal no encontrada.")

    return Alcance(branch_id=destino, branch_ids=alcanzables)


SucursalActiva = Annotated[Alcance, Depends(sucursal_activa)]
