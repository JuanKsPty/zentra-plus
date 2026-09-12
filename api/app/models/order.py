from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.schemas import ConHoraDelHecho, ConIdDelCliente, Entrada
from app.db.types import Dinero, TimestampTZ
from app.models.base import ConSucursal, IdUUID, Timestamps, ahora_utc

# De donde viene una comanda. `counter` NO se puede pedir en el cuerpo de
# `POST /orders`: lo escribe unicamente la venta de mostrador, que cobra en el
# mismo acto. Si se pudiera pedir, cualquiera con `orders:write` —un mesero—
# podria marcar una comanda normal como venta de mostrador y hacerla desaparecer
# del tablero de cocina SIN COBRARLA.
ORIGENES = ("staff", "counter")
ORIGENES_PEDIBLES = ("staff",)


class Order(ConSucursal, IdUUID, Timestamps, table=True):
    __tablename__ = "orders"

    # Numero legible, del contador de la sucursal. Es lo que se canta en voz
    # alta y lo que aparece en el recibo.
    order_number: int

    # Para las que no tienen mesa: «Mostrador», «Para llevar».
    label: str | None = Field(default=None, max_length=80)
    table_id: UUID | None = Field(default=None, foreign_key="tables.id", ondelete="SET NULL")
    waiter_id: UUID | None = Field(default=None, foreign_key="users.id")
    shift_id: UUID | None = Field(default=None, index=True)

    source: str = Field(default="staff", max_length=20)
    status: str = Field(default="pending", max_length=20)
    notes: str | None = Field(default=None, max_length=500)

    subtotal: Decimal = Field(default=Decimal("0.00"), sa_type=Dinero)
    tip_amount: Decimal = Field(default=Decimal("0.00"), sa_type=Dinero)
    total: Decimal = Field(default=Decimal("0.00"), sa_type=Dinero)

    # Cuando paso DE VERDAD, segun el dispositivo. Aparte de `created_at`, que es
    # cuando llego. Para la cocina y para los tiempos de preparacion importa lo
    # primero. Se lee siempre como `occurred_at or created_at`.
    occurred_at: datetime | None = Field(default=None, sa_type=TimestampTZ)

    __table_args__ = (
        # La red que convierte una restauracion mal hecha o un INSERT a mano en
        # un error inmediato, en vez de en dos cuentas con el mismo numero.
        Index("uq_orders_numero_por_sucursal", "branch_id", "order_number", unique=True),
        # El indice que sostiene TODAS las pantallas operativas: «las cuentas
        # vivas de mi sucursal».
        Index("idx_orders_abiertas", "branch_id", "status", "created_at"),
        Index("idx_orders_mesa", "table_id"),
    )


class OrderItem(IdUUID, table=True):
    """
    Una linea. NO lleva `branch_id`: lo hereda de la comanda.

    Duplicarlo abriria la puerta a que discrepen, y los reportes por sucursal se
    unen con `orders`, que ya esta indexada.
    """

    __tablename__ = "order_items"

    order_id: UUID = Field(foreign_key="orders.id", ondelete="CASCADE", index=True)
    product_id: UUID = Field(foreign_key="products.id", ondelete="RESTRICT")

    # Copia del nombre y del precio EN EL MOMENTO del pedido. Cambiar el precio
    # manana no puede reescribir lo que un cliente ya pago, y renombrar un
    # producto no puede reescribir un recibo impreso.
    product_name: str = Field(max_length=150)
    unit_price: Decimal = Field(sa_type=Dinero)
    station: str = Field(max_length=20)

    quantity: int = Field(ge=1)
    subtotal: Decimal = Field(sa_type=Dinero)
    notes: str | None = Field(default=None, max_length=255)
    status: str = Field(default="pending", max_length=20)
    created_at: datetime = Field(default_factory=ahora_utc, sa_type=TimestampTZ)


class OrderStatusHistory(IdUUID, table=True):
    """
    Cada cambio de estado.

    Existe desde el primer commit de comandas porque es IMPOSIBLE de reconstruir
    hacia atras: si no entra ahora, las metricas de tiempo de preparacion solo
    tendran datos desde el dia que alguien se acuerde de anadirla.
    """

    __tablename__ = "order_status_history"

    order_id: UUID = Field(foreign_key="orders.id", ondelete="CASCADE", index=True)
    from_status: str | None = Field(default=None, max_length=20)
    to_status: str = Field(max_length=20)
    changed_by: UUID | None = Field(default=None)
    occurred_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    changed_at: datetime = Field(default_factory=ahora_utc, sa_type=TimestampTZ)

    __table_args__ = (Index("idx_historial_estado", "to_status", "changed_at"),)


# --- entrada ----------------------------------------------------------------


class LineaNueva(Entrada, ConIdDelCliente):
    product_id: UUID
    quantity: int = Field(default=1, ge=1, le=99)
    notes: str | None = Field(default=None, max_length=255)


class OrdenNueva(Entrada, ConIdDelCliente, ConHoraDelHecho):
    table_id: UUID | None = None
    label: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=500)
    items: list[LineaNueva] = []


class LineaAnadida(Entrada, ConIdDelCliente, ConHoraDelHecho):
    product_id: UUID
    quantity: int = Field(default=1, ge=1, le=99)
    notes: str | None = Field(default=None, max_length=255)


class CambioDeEstado(Entrada, ConHoraDelHecho):
    status: str = Field(max_length=20)


# --- salida -----------------------------------------------------------------


class OrderItemPublic(SQLModel):
    id: UUID
    product_id: UUID
    product_name: str
    unit_price: Decimal
    station: str
    quantity: int
    subtotal: Decimal
    notes: str | None
    status: str


class OrderPublic(SQLModel):
    id: UUID
    order_number: int
    label: str | None
    table_id: UUID | None
    table_number: int | None = None
    waiter_id: UUID | None
    source: str
    status: str
    notes: str | None
    subtotal: Decimal
    tip_amount: Decimal
    total: Decimal
    occurred_at: datetime
    created_at: datetime
    items: list[OrderItemPublic] = []
