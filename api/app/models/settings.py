from decimal import Decimal
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.db.types import Dinero
from app.models.base import IdUUID, Timestamps


class BusinessConfigBase(SQLModel):
    business_name: str = Field(min_length=2, max_length=150)
    # El nombre fiscal, que casi nunca es el comercial y es el que va al recibo.
    legal_name: str | None = Field(default=None, max_length=180)
    tax_id: str | None = Field(default=None, max_length=40)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    # El impuesto YA VA INCLUIDO en los precios del catalogo. El recibo lo
    # desglosa hacia atras (`total * tasa / (1 + tasa)`), que es como lo espera
    # el cliente: lo que ve en la carta es lo que paga.
    tax_rate: Decimal = Field(default=Decimal("0.00"), sa_type=Dinero)

    receipt_footer: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)


class BusinessConfig(BusinessConfigBase, IdUUID, Timestamps, table=True):
    """
    Los datos del negocio. UNA fila, y la base lo garantiza.

    Es del negocio y no de la sucursal: el nombre fiscal y la moneda son los
    mismos en todas las sedes. Lo que si cambia por sede —direccion, telefono,
    zona horaria— vive en `branches`.

    La unicidad la impone un indice unico sobre una expresion constante, no una
    comprobacion en el servicio: un read-then-write deja una ventana por la que
    dos peticiones simultaneas crean dos filas, y a partir de ahi «la
    configuracion» depende de cual lea cada consulta.
    """

    __tablename__ = "business_config"


class BusinessConfigUpdate(SQLModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=150)
    legal_name: str | None = Field(default=None, max_length=180)
    tax_id: str | None = Field(default=None, max_length=40)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    tax_rate: Decimal | None = Field(default=None, ge=0, le=1)
    receipt_footer: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)


class BusinessConfigPublic(BusinessConfigBase):
    id: UUID
