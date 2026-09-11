"""
Los manejadores que hacen que TODA respuesta de error tenga la misma forma.

Hay cuatro porque hay cuatro fuentes de error distintas, y la mas importante es
la segunda: si se deja pasar el `detail` de FastAPI tal cual, un 422 llega al
navegador como una lista de objetos y cada formulario acaba inventandose como
leerla. Traducirlo aqui, una vez, es lo que permite que el cliente tenga un solo
camino para pintar un error de campo.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import CuerpoError, DetalleError, ErrorAplicacion, RespuestaError

logger = logging.getLogger("zentra.errores")

# Los mensajes de Pydantic vienen en ingles y hablan de tipos, no de formularios.
# Se traducen los que un usuario puede provocar de verdad; el resto cae al
# mensaje generico, que es preferible a una frase en ingles a medio traducir.
_MENSAJES: dict[str, str] = {
    "missing": "Hace falta este dato.",
    "string_too_short": "Es demasiado corto.",
    "string_too_long": "Es demasiado largo.",
    "string_pattern_mismatch": "No tiene el formato esperado.",
    "value_error": "El valor no es valido.",
    "int_parsing": "Tiene que ser un numero entero.",
    "float_parsing": "Tiene que ser un numero.",
    "decimal_parsing": "Tiene que ser un importe.",
    "bool_parsing": "Tiene que ser verdadero o falso.",
    "uuid_parsing": "No es un identificador valido.",
    "datetime_from_date_parsing": "No es una fecha valida.",
    "greater_than": "Tiene que ser mayor.",
    "greater_than_equal": "Es demasiado bajo.",
    "less_than": "Tiene que ser menor.",
    "less_than_equal": "Es demasiado alto.",
    "enum": "No es una de las opciones permitidas.",
    "extra_forbidden": "Este campo no se acepta aqui.",
}

_CODIGOS_HTTP: dict[int, str] = {
    400: "peticion_invalida",
    401: "sin_sesion",
    403: "sin_permiso",
    404: "no_encontrado",
    405: "metodo_no_permitido",
    409: "conflicto",
    422: "datos_invalidos",
    429: "demasiadas_peticiones",
}


def _responder(status_code: int, cuerpo: CuerpoError) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=RespuestaError(error=cuerpo).model_dump())


def _campo(loc: tuple) -> str | None:
    """
    El nombre del campo, tal como lo conoce el formulario.

    `loc` de Pydantic empieza por el origen ("body", "query", "path") y puede
    llevar indices de lista por el medio. Al formulario le sirve el ultimo
    segmento que sea texto; un indice no le dice nada.
    """
    for parte in reversed(loc):
        if isinstance(parte, str) and parte not in {"body", "query", "path", "header"}:
            return parte
    return None


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorAplicacion)
    async def _error_de_negocio(request: Request, exc: ErrorAplicacion) -> JSONResponse:
        # Los errores de negocio son respuestas esperadas, no fallos: van a
        # nivel informativo. Registrarlos como error llenaria de trazas los
        # tests que los provocan a proposito, y el ruido acaba tapando lo grave.
        logger.info("%s %s -> %s", request.method, request.url.path, exc.code)
        return _responder(
            exc.status_code,
            CuerpoError(code=exc.code, message=exc.message, details=exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _datos_invalidos(request: Request, exc: RequestValidationError) -> JSONResponse:
        detalles = [
            DetalleError(
                field=_campo(error["loc"]),
                message=_MENSAJES.get(error["type"], "El valor no es valido."),
            )
            for error in exc.errors()
        ]
        return _responder(
            422,
            CuerpoError(
                code="datos_invalidos",
                message="Revisa los datos: hay algo que no encaja.",
                details=detalles,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _error_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        mensaje = exc.detail if isinstance(exc.detail, str) else "La peticion no se pudo atender."
        return _responder(
            exc.status_code,
            CuerpoError(code=_CODIGOS_HTTP.get(exc.status_code, "error"), message=mensaje),
        )

    @app.exception_handler(Exception)
    async def _error_no_previsto(request: Request, exc: Exception) -> JSONResponse:
        # El mensaje de la excepcion NO viaja al cliente, y no es pudor: `str()`
        # de un error de SQLAlchemy incluye los parametros enlazados de la
        # consulta, asi que un insert fallido en la tabla de usuarios pondria un
        # hash de credencial en la respuesta. Al log va la traza; al cliente,
        # una frase.
        logger.exception("Error no manejado en %s %s", request.method, request.url.path)
        return _responder(
            500,
            CuerpoError(code="error_interno", message="Error interno del servidor."),
        )
