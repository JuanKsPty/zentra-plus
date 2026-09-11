"""
El formato de error de la API, decidido antes del primer endpoint que lo use.

Todo error sale con la misma forma:

    {"error": {"code": "...", "message": "...", "details": [...], "request_id": "..."}}

`code` es estable y lo lee el cliente para decidir que hacer; `message` esta en
espanol y es lo que ve una persona. Los dos hacen falta: un `code` sin mensaje
obliga al frontend a mantener un diccionario de traducciones, y un mensaje sin
codigo obliga a comparar cadenas, que se rompe en cuanto alguien corrige una
tilde.
"""

from pydantic import BaseModel, Field


class DetalleError(BaseModel):
    """Un problema concreto, normalmente en un campo del cuerpo."""

    field: str | None = None
    message: str


class CuerpoError(BaseModel):
    code: str
    message: str
    details: list[DetalleError] = Field(default_factory=list)
    # Reservado desde ya aunque el registro estructurado llegue mas adelante:
    # anadir el campo despues obligaria a tocar todos los manejadores y todas
    # las pruebas de error a la vez.
    request_id: str | None = None


class RespuestaError(BaseModel):
    error: CuerpoError


class ErrorAplicacion(Exception):
    """
    Un error de negocio, con su codigo y su mensaje para la persona.

    Se usa en vez de HTTPException para que el mensaje de cara al usuario sea
    parte de la regla y no un detalle del transporte: quien escribe la regla de
    «una cuenta no se cierra con saldo» es quien mejor sabe que decirle al
    cajero.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[DetalleError] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


class NoEncontrado(ErrorAplicacion):
    def __init__(self, message: str = "No se encontro lo que buscabas.") -> None:
        super().__init__(404, "no_encontrado", message)


class Conflicto(ErrorAplicacion):
    """El estado actual no permite la operacion. No es un error de validacion."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(409, code, message)
