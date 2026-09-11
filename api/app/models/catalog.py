from decimal import Decimal
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.db.types import Dinero
from app.models.base import IdUUID, Timestamps

# Donde se prepara cada cosa. Decide en que tablero aparece la linea: la cerveza
# no va a la cocina y el postre no va a la barra.
ESTACIONES = ("kitchen", "bar", "immediate")


class CategoryBase(SQLModel):
    name: str = Field(min_length=2, max_length=80)
    sort_order: int = 0
    is_active: bool = True


class Category(CategoryBase, IdUUID, Timestamps, table=True):
    """
    Una seccion de la carta. Del NEGOCIO, no de la sucursal.

    El catalogo se define una vez y se hereda en todas las sedes: es la mitad del
    modelo multisucursal. Lo que cambia por local es el precio, la
    disponibilidad y las existencias, y eso vive en `product_branch`.
    """

    __tablename__ = "categories"


class ProductBase(SQLModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal = Field(sa_type=Dinero, ge=0)
    station: str = Field(default="kitchen", max_length=20)
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class Product(ProductBase, IdUUID, Timestamps, table=True):
    __tablename__ = "products"

    category_id: UUID | None = Field(
        default=None, foreign_key="categories.id", ondelete="SET NULL", index=True
    )


class ProductBranch(SQLModel, table=True):
    """
    Lo que cambia de un producto EN UNA SUCURSAL.

    La fila SOLO EXISTE SI HAY ALGO QUE DECIR. Ausencia significa herencia pura,
    y eso evita tener que sembrar N x M filas al dar de alta una sucursal — que
    es el error obvio de este diseno y el que lo vuelve inmanejable con cuatro
    sedes y trescientos productos.

    No hereda `ConSucursal`: la sucursal es parte de su clave primaria, no una
    columna de alcance. Filtrarla con `consulta()` no tendria sentido, porque
    siempre se consulta unida al producto.
    """

    __tablename__ = "product_branch"

    product_id: UUID = Field(foreign_key="products.id", primary_key=True, ondelete="CASCADE")
    branch_id: UUID = Field(foreign_key="branches.id", primary_key=True, ondelete="CASCADE")
    # Nulo = hereda el del producto. No se copia el precio base al crear la fila:
    # si se copiara, cambiar el precio del negocio dejaria de llegar a las sedes
    # que solo querian marcar «agotado».
    price: Decimal | None = Field(default=None, sa_type=Dinero, ge=0)
    # «Hoy no queda». Lo cambia el salon, no el administrador.
    is_available: bool = True
    # «Esta sucursal no lo vende». Lo cambia el administrador.
    is_listed: bool = True


class ModifierGroupBase(SQLModel):
    name: str = Field(min_length=2, max_length=80)
    is_required: bool = False
    allow_multiple: bool = False
    min_selections: int = Field(default=0, ge=0)
    max_selections: int | None = Field(default=None, ge=1)
    sort_order: int = 0
    is_active: bool = True


class ModifierGroup(ModifierGroupBase, IdUUID, Timestamps, table=True):
    """«Termino de la carne», «Extras», «Tamano»."""

    __tablename__ = "modifier_groups"


class ModifierOptionBase(SQLModel):
    name: str = Field(min_length=1, max_length=80)
    # Puede ser NEGATIVO: «sin queso, -0.50» es tan valido como «extra queso».
    price_adjustment: Decimal = Field(default=Decimal("0.00"), sa_type=Dinero)
    sort_order: int = 0
    is_active: bool = True


class ModifierOption(ModifierOptionBase, IdUUID, table=True):
    __tablename__ = "modifier_options"

    group_id: UUID = Field(foreign_key="modifier_groups.id", ondelete="CASCADE", index=True)


class ProductModifierGroup(SQLModel, table=True):
    __tablename__ = "product_modifier_groups"

    product_id: UUID = Field(foreign_key="products.id", primary_key=True, ondelete="CASCADE")
    group_id: UUID = Field(foreign_key="modifier_groups.id", primary_key=True, ondelete="CASCADE")
    sort_order: int = 0


# --- esquemas de entrada y salida -------------------------------------------


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryPublic(CategoryBase):
    id: UUID


class ProductCreate(ProductBase):
    category_id: UUID | None = None


class ProductUpdate(SQLModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    price: Decimal | None = Field(default=None, ge=0)
    station: str | None = Field(default=None, max_length=20)
    image_url: str | None = Field(default=None, max_length=500)
    category_id: UUID | None = None
    is_active: bool | None = None


class ProductPublic(ProductBase):
    id: UUID
    category_id: UUID | None
    # El precio YA RESUELTO para la sucursal de la peticion, y la disponibilidad
    # de ahi. Quien consume esto no tiene que saber que existe `product_branch`,
    # que es justo lo que evita que media aplicacion aprenda a resolver precios.
    effective_price: Decimal
    is_available: bool


class ProductBranchUpdate(SQLModel):
    price: Decimal | None = Field(default=None, ge=0)
    is_available: bool | None = None
    is_listed: bool | None = None


class ModifierGroupCreate(ModifierGroupBase):
    options: list[ModifierOptionBase] = []


class ModifierGroupPublic(ModifierGroupBase):
    id: UUID
    options: list["ModifierOptionPublic"] = []


class ModifierOptionPublic(ModifierOptionBase):
    id: UUID
