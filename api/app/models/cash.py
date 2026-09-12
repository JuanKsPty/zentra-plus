from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Index, text
from sqlmodel import Field, SQLModel

from app.core.schemas import ConClaveDeReenvio, ConHoraDelHecho, Entrada
from app.db.types import Dinero, TimestampTZ
from app.models.base import ConSucursal, IdUUID, ahora_utc

ESTADOS_DE_TURNO = ("open", "closed")


class Shift(ConSucursal, IdUUID, table=True):
    """
    Un turno de caja.

    Es POR CAJERO Y SUCURSAL. Un gerente que cubre dos sedes tiene que poder
    tener una caja abierta en cada una — en LoklFlow el indice era solo sobre el
    cajero y eso lo impedia.
    """

    __tablename__ = "shifts"

    opened_by: UUID = Field(foreign_key="users.id", index=True)
    closed_by: UUID | None = Field(default=None, foreign_key="users.id")
    opened_at: datetime = Field(default_factory=ahora_utc, sa_type=TimestampTZ)
    closed_at: datetime | None = Field(default=None, sa_type=TimestampTZ)

    opening_cash: Decimal = Field(sa_type=Dinero, ge=0)
    closing_cash: Decimal | None = Field(default=None, sa_type=Dinero)
    notes: str | None = Field(default=None, max_length=500)
    status: str = Field(default="open", max_length=10)

    __table_args__ = (
        # UN TURNO ABIERTO POR CAJERO Y SUCURSAL.
        #
        # Indice PARCIAL —solo los abiertos— porque los cerrados se acumulan sin
        # limite: uno normal impediria abrir caja dos dias seguidos.
        #
        # La comprobacion previa en el servicio da el mensaje bueno en el caso
        # normal; esto cierra la ventana que deja abierta. Sin el, un doble clic
        # abre dos turnos, los cobros se reparten entre los dos y NINGUNO
        # cuadra — que es peor que no cuadrar uno, porque nadie sabe cual mirar.
        Index(
            "idx_shifts_un_abierto_por_cajero_y_sucursal",
            "opened_by",
            "branch_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        Index("idx_shifts_branch_opened", "branch_id", "opened_at"),
    )


class Payment(ConSucursal, IdUUID, table=True):
    """
    Un cobro. Varios por cuenta: asi funciona pagar a medias.

    Lleva `branch_id` DENORMALIZADO desde la comanda. El arqueo y los reportes
    de caja agregan por sucursal, y unir con `orders` fila a fila para saber de
    donde es cada cobro es trabajo que se puede ahorrar — ademas de que una
    venta de mostrador y una de mesa tienen que sumar igual.
    """

    __tablename__ = "payments"

    order_id: UUID = Field(foreign_key="orders.id", ondelete="CASCADE", index=True)
    shift_id: UUID | None = Field(default=None, foreign_key="shifts.id", index=True)

    method: str = Field(max_length=20)
    amount: Decimal = Field(sa_type=Dinero, gt=0)
    reference: str | None = Field(default=None, max_length=100)

    # Reconoce un reenvio. Un cobro no trae identificador propio —lo pone el
    # servidor— asi que sin esto un pago parcial repetido se cobra dos veces: el
    # completo se rechaza de rebote porque la cuenta ya esta cerrada, pero
    # 30 + 30 sobre una cuenta de 100 pasa entero.
    client_request_id: str | None = Field(default=None, max_length=64)

    processed_by: UUID | None = Field(default=None, foreign_key="users.id")
    occurred_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    processed_at: datetime = Field(default_factory=ahora_utc, sa_type=TimestampTZ)

    __table_args__ = (
        # Unico PARCIAL: solo indexa las filas que traen clave, que son las
        # menos. En PostgreSQL varios NULL no chocan de todas formas, pero asi
        # el indice ni siquiera las guarda.
        Index(
            "idx_payments_client_request_id",
            "client_request_id",
            unique=True,
            postgresql_where=text("client_request_id IS NOT NULL"),
        ),
        Index("idx_payments_branch_processed", "branch_id", "processed_at"),
    )


# --- entrada ----------------------------------------------------------------


class AbrirTurno(Entrada):
    opening_cash: Decimal = Field(ge=0)
    notes: str | None = Field(default=None, max_length=500)


class CerrarTurno(Entrada):
    closing_cash: Decimal = Field(ge=0)
    notes: str | None = Field(default=None, max_length=500)


class CobroNuevo(Entrada, ConClaveDeReenvio, ConHoraDelHecho):
    method: str = Field(max_length=20)
    # El importe SI viaja, porque pagar a medias es decidir cuanto pone cada
    # uno. Lo que no viaja es el TOTAL de la cuenta: ese lo sabe el servidor,
    # con el precio de la sucursal.
    amount: Decimal = Field(gt=0)
    reference: str | None = Field(default=None, max_length=100)


class PropinaNueva(Entrada, ConHoraDelHecho):
    tip_amount: Decimal = Field(ge=0)


# --- salida -----------------------------------------------------------------


class PaymentPublic(SQLModel):
    id: UUID
    method: str
    amount: Decimal
    reference: str | None
    processed_at: datetime


class EstadoDeCobro(SQLModel):
    order_id: UUID
    total: Decimal
    paid: Decimal
    due: Decimal
    is_settled: bool
    payments: list[PaymentPublic] = []


class ShiftPublic(SQLModel):
    id: UUID
    opened_by: UUID
    opened_at: datetime
    closed_at: datetime | None
    opening_cash: Decimal
    closing_cash: Decimal | None
    status: str
    notes: str | None


class ArqueoPublic(SQLModel):
    shift: ShiftPublic
    by_method: dict[str, Decimal]
    total_sold: Decimal
    cash_sold: Decimal
    expected_cash: Decimal
    counted_cash: Decimal | None
    difference: Decimal | None
    payments_count: int
