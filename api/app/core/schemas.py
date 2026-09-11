"""
Las bases de los esquemas de entrada.

Dos decisiones que afectan a todo cuerpo que la API acepte.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Entrada(BaseModel):
    """
    Base de todo cuerpo de peticion.

    `extra="forbid"` es el equivalente del `forbidNonWhitelisted` de Nest: un
    campo que la API no declara devuelve 422 en vez de ignorarse. Ignorarlo es
    peor de lo que parece — un cliente que manda `precio` donde la API espera
    `price` cree que funciono y descubre el problema cuando alguien mira los
    numeros.
    """

    model_config = ConfigDict(extra="forbid")


class ConHoraDelHecho(BaseModel):
    """
    Para los cuerpos que una cola de reenvios va a repetir algun dia.

    El campo SE DECLARA YA, aunque hoy nadie lo mande y el modo sin conexion sea
    de una fase posterior. El motivo es `extra="forbid"`: un campo no declarado
    da 422, y para una cola un 422 es un fallo DEFINITIVO — no se reintenta. Se
    perderia la comanda por un sello de hora. Anadirlo cuando la cola ya exista
    significa desplegar la API antes que el cliente y rezar por el orden.
    """

    occurred_at: datetime | None = Field(
        default=None,
        description=(
            "Cuando ocurrio de verdad, segun el dispositivo. Si falta, la hora del servidor."
        ),
    )


class ConIdDelCliente(BaseModel):
    """
    Para lo que el dispositivo crea: la comanda y sus lineas.

    El identificador lo acuna el cliente, y eso es lo que hace que reenviar no
    duplique: el servidor busca antes de escribir y, si ya existe, devuelve lo
    que hay. La comprobacion es leer-antes-de-escribir y NUNCA cazar la
    violacion de unicidad — un `merge()` con clave existente hace UPDATE y
    sobreescribiria en silencio lo que se anadio despues.
    """

    id: UUID | None = Field(
        default=None,
        description="Identificador acunado por el dispositivo. Reenviar con el mismo no duplica.",
    )


class ConClaveDeReenvio(BaseModel):
    """
    Para lo que mueve dinero, donde no hay un identificador natural que reusar.

    Un cobro no trae id propio —el servidor le pone uno—, asi que el reenvio se
    reconoce por una clave que genera el cliente. Sin ella, un pago parcial
    reenviado se cobra dos veces: el completo se rechaza de rebote porque la
    cuenta ya esta cerrada, pero 30 + 30 sobre una cuenta de 100 pasa entero.
    """

    client_request_id: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "Clave del cliente para reconocer un reenvio. "
            "Cobrar dos veces con la misma no cobra dos veces."
        ),
    )
