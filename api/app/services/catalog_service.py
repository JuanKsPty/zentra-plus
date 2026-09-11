"""
El catalogo, y la unica funcion que resuelve el precio de una sucursal.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.errors import NoEncontrado
from app.db.scoping import Alcance
from app.models import Product, ProductBranch, ProductPublic


def consulta_de_productos(alcance: Alcance):
    """
    Productos con su precio y disponibilidad YA RESUELTOS para la sucursal.

    El `LEFT JOIN` con `product_branch` es lo que hace que la ausencia de fila
    signifique herencia. Si fuera un JOIN normal, un producto sin override
    desapareceria del catalogo de esa sede — y el sintoma seria «faltan productos
    en la sucursal nueva», que nadie relaciona con el tipo de join.

    Va aqui y no en cada endpoint porque si media aplicacion aprende a resolver
    precios, el dia que haya que cambiar la regla hay que encontrarlos todos.
    """
    override = col(ProductBranch.price)
    return select(
        Product,
        func.coalesce(override, col(Product.price)).label("effective_price"),
        func.coalesce(col(ProductBranch.is_available), True).label("is_available"),
        func.coalesce(col(ProductBranch.is_listed), True).label("is_listed"),
    ).join(
        ProductBranch,
        (col(ProductBranch.product_id) == col(Product.id))
        & (col(ProductBranch.branch_id) == alcance.branch_id),
        isouter=True,
    )


def a_publico(fila) -> ProductPublic:
    producto, precio_efectivo, disponible, _listado = fila
    return ProductPublic(
        id=producto.id,
        name=producto.name,
        description=producto.description,
        price=producto.price,
        station=producto.station,
        image_url=producto.image_url,
        is_active=producto.is_active,
        category_id=producto.category_id,
        effective_price=precio_efectivo,
        is_available=disponible,
    )


def precio_efectivo(session: Session, producto_id: UUID, alcance: Alcance) -> Decimal:
    """
    El precio con el que se cobra un producto EN ESTA SUCURSAL.

    Lo llama quien arma una comanda para fijar el precio de la linea, que se
    guarda como copia: cambiar el precio manana no puede reescribir lo que un
    cliente ya pago.
    """
    fila = session.exec(
        consulta_de_productos(alcance).where(col(Product.id) == producto_id)
    ).first()
    if fila is None:
        raise NoEncontrado("Ese producto no existe.")
    return fila[1]
