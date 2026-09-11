from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.db.types import TimestampTZ


def ahora_utc() -> datetime:
    return datetime.now(UTC)


class IdUUID(SQLModel):
    """
    Clave primaria UUID generada en Python, no por la base.

    Es lo que permite que el dispositivo acune el id antes de enviar: reenviar
    la misma comanda no crea una segunda. La cola sin conexion llega mas
    adelante, pero si el id lo pusiera la base habria que reescribir el dominio
    entero para meterla.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)


class Timestamps(SQLModel):
    created_at: datetime = Field(default_factory=ahora_utc, sa_type=TimestampTZ)
    updated_at: datetime = Field(
        default_factory=ahora_utc,
        sa_type=TimestampTZ,
        sa_column_kwargs={"onupdate": ahora_utc},
    )


class ConSucursal(SQLModel):
    """
    Marca que una tabla pertenece a una sucursal concreta.

    No es decoracion: el constructor de consultas y la prueba que vigila el
    alcance enumeran las subclases de esto para saber que tablas TIENEN que ir
    filtradas. Heredarlo es lo que mete una tabla en esa lista.

    Lo llevan las tablas de la operacion —salon, comandas, caja, existencias—
    y no lo llevan el catalogo ni los roles, que son del negocio entero: el menu
    se define una vez y se hereda en todas las sedes.
    """

    branch_id: UUID = Field(foreign_key="branches.id", index=True)
