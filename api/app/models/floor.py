from datetime import datetime
from uuid import UUID

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.db.types import TimestampTZ
from app.models.base import ConSucursal, IdUUID, Timestamps, ahora_utc

# Los cinco estados de una mesa. `cleaning` existe porque una mesa recien
# cobrada no esta libre: hay que recogerla, y si el sistema dice que esta libre
# el anfitrion sienta a alguien encima de los platos del anterior.
ESTADOS_DE_MESA = ("available", "occupied", "cleaning", "reserved", "maintenance")

FORMAS_DE_MESA = ("square", "round")


class SectorBase(SQLModel):
    name: str = Field(min_length=2, max_length=80)
    sort_order: int = 0
    is_active: bool = True


class Sector(SectorBase, ConSucursal, IdUUID, Timestamps, table=True):
    """Una zona del local: interior, terraza, barra."""

    __tablename__ = "sectors"

    __table_args__ = (
        # «Terraza» puede existir en las dos sedes. Lo que no puede haber son dos
        # terrazas en la misma.
        Index("uq_sectors_nombre_por_sucursal", "branch_id", "name", unique=True),
    )


class TableBase(SQLModel):
    number: int = Field(ge=1)
    capacity: int = Field(default=4, ge=1, le=50)
    shape: str = Field(default="square", max_length=10)
    position_x: int | None = None
    position_y: int | None = None
    is_active: bool = True


class RestaurantTable(TableBase, ConSucursal, IdUUID, Timestamps, table=True):
    """
    Una mesa.

    En LoklFlow el numero era unico GLOBAL, lo que con dos sedes significa que la
    segunda no puede tener una «mesa 1» — absurdo operativamente. Aqui la
    unicidad es por sucursal.
    """

    __tablename__ = "tables"

    sector_id: UUID = Field(foreign_key="sectors.id", ondelete="CASCADE", index=True)
    status: str = Field(default="available", max_length=20)

    # Aparte de `updated_at`, y no es duplicado: es la marca que permite decidir
    # quien gana cuando dos dispositivos cambian la misma mesa. `updated_at` se
    # mueve tambien al renombrarla o al arrastrarla en el mapa, que no son
    # cambios de estado y no deberian contar para ese desempate.
    status_changed_at: datetime = Field(default_factory=ahora_utc, sa_type=TimestampTZ)

    __table_args__ = (
        Index("uq_tables_numero_por_sucursal", "branch_id", "number", unique=True),
        # El indice que van a usar todas las pantallas operativas: «las mesas de
        # mi sucursal, por estado».
        Index("idx_tables_branch_status", "branch_id", "status"),
    )


# --- esquemas ---------------------------------------------------------------


class SectorCreate(SectorBase):
    pass


class SectorUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    sort_order: int | None = None
    is_active: bool | None = None


class SectorPublic(SectorBase):
    id: UUID


class TableCreate(TableBase):
    sector_id: UUID


class TableUpdate(SQLModel):
    number: int | None = Field(default=None, ge=1)
    capacity: int | None = Field(default=None, ge=1, le=50)
    shape: str | None = Field(default=None, max_length=10)
    sector_id: UUID | None = None
    is_active: bool | None = None


class TableStatusUpdate(SQLModel):
    status: str = Field(max_length=20)


class TableLayoutItem(SQLModel):
    id: UUID
    position_x: int
    position_y: int


class TableLayoutUpdate(SQLModel):
    """
    El mapa entero, en una sola peticion.

    Arrastrar seis mesas y mandar seis PATCH deja el mapa a medias si la red se
    corta en la tercera, y el operario no tiene forma de saber cuales llegaron.
    """

    tables: list[TableLayoutItem]


class TablePublic(TableBase):
    id: UUID
    sector_id: UUID
    status: str
