from uuid import UUID

from sqlmodel import Field, SQLModel

from app.models.base import IdUUID, Timestamps


class BranchBase(SQLModel):
    name: str = Field(min_length=2, max_length=120)
    # Codigo corto y estable. Es lo que aparece en un CSV, en un selector y en
    # una conversacion («lo de NORTE»), donde un uuid no sirve de nada.
    code: str = Field(min_length=2, max_length=20)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    # Propia, porque una cadena puede cruzar husos. Manda en todo calculo por
    # dia: el cierre de «hoy» se corta a medianoche AQUI.
    timezone: str = Field(default="America/Panama", max_length=50)
    is_active: bool = True
    sort_order: int = 0


class Branch(BranchBase, IdUUID, Timestamps, table=True):
    __tablename__ = "branches"

    code: str = Field(min_length=2, max_length=20, unique=True)
    # La que se preselecciona cuando alguien entra y no ha elegido nada. No es
    # un indice unico parcial porque no hay drama en que haya dos: se coge la
    # primera por `sort_order`. Forzarlo obligaria a una transaccion para mover
    # la marca de una sucursal a otra, y eso no compra nada.
    is_default: bool = False


class BranchCounter(SQLModel, table=True):
    """
    El contador del numero de cuenta, uno por sucursal.

    Existe porque el numero de cuenta tiene que reiniciarse por local: la mesa 1
    de dos sedes distintas no comparte numeracion, y un cajero que ve saltar los
    numeros (1, 4, 7) pregunta que paso con los que faltan.

    POR QUE UNA FILA CONTADOR Y NO UNA SECUENCIA

    Una secuencia por sucursal obligaria a ejecutar DDL cada vez que se da de
    alta un local, desde codigo de aplicacion, y eso rompe la propiedad de que
    el esquema sale de las migraciones. Con `UPDATE ... RETURNING` sobre esta
    fila, PostgreSQL bloquea UNA fila y la segunda peticion espera al COMMIT de
    la primera: no falla, espera. Y a diferencia de una secuencia, el numero se
    devuelve si la transaccion aborta, asi que no deja huecos.

    Lo que NO se hace nunca es `MAX(order_number) + 1`: dos lecturas ven el
    mismo maximo y entregan el mismo numero.
    """

    __tablename__ = "branch_counters"

    branch_id: UUID = Field(
        foreign_key="branches.id",
        primary_key=True,
        ondelete="CASCADE",
    )
    last_order_number: int = Field(default=0)


class BranchCreate(BranchBase):
    pass


class BranchUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    timezone: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None
    sort_order: int | None = None


class BranchPublic(BranchBase):
    id: UUID
    is_default: bool
