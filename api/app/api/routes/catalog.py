from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import col, select

from app.core import permissions as P
from app.core.deps import SessionDep, SucursalActiva, requiere
from app.core.errors import NoEncontrado
from app.core.pagination import Pagina, Paginacion, paginar
from app.models import (
    ESTACIONES,
    Category,
    CategoryCreate,
    CategoryPublic,
    CategoryUpdate,
    Product,
    ProductBranch,
    ProductBranchUpdate,
    ProductCreate,
    ProductPublic,
    ProductUpdate,
)
from app.services import catalog_service

router = APIRouter(prefix="/catalog", tags=["catalogo"])


# --- categorias -------------------------------------------------------------


@router.get(
    "/categories", dependencies=[Depends(requiere(P.CATALOG_READ))], summary="Las secciones"
)
def listar_categorias(session: SessionDep, incluir_inactivas: bool = False) -> list[CategoryPublic]:
    consulta = select(Category)
    if not incluir_inactivas:
        consulta = consulta.where(col(Category.is_active).is_(True))
    filas = session.exec(consulta.order_by(col(Category.sort_order), col(Category.name))).all()
    return [CategoryPublic.model_validate(f, from_attributes=True) for f in filas]


@router.post(
    "/categories",
    status_code=201,
    dependencies=[Depends(requiere(P.CATALOG_WRITE))],
    summary="Crear seccion",
)
def crear_categoria(datos: CategoryCreate, session: SessionDep) -> CategoryPublic:
    categoria = Category.model_validate(datos)
    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    return CategoryPublic.model_validate(categoria, from_attributes=True)


@router.patch(
    "/categories/{categoria_id}",
    dependencies=[Depends(requiere(P.CATALOG_WRITE))],
    summary="Editar seccion",
)
def editar_categoria(
    categoria_id: UUID, datos: CategoryUpdate, session: SessionDep
) -> CategoryPublic:
    categoria = session.get(Category, categoria_id)
    if categoria is None:
        raise NoEncontrado("Esa seccion no existe.")

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(categoria, campo, valor)
    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    return CategoryPublic.model_validate(categoria, from_attributes=True)


@router.delete(
    "/categories/{categoria_id}",
    dependencies=[Depends(requiere(P.CATALOG_WRITE))],
    summary="Retirar seccion",
)
def retirar_categoria(categoria_id: UUID, session: SessionDep) -> CategoryPublic:
    """
    BAJA LOGICA, nunca DELETE.

    Un producto borrado de verdad convierte en basura toda cuenta historica que
    lo referencia, y los reportes empiezan a fallar con claves rotas meses
    despues. Retirar es poner `is_active` en falso: desaparece de la carta y
    sigue existiendo para el pasado.
    """
    categoria = session.get(Category, categoria_id)
    if categoria is None:
        raise NoEncontrado("Esa seccion no existe.")

    categoria.is_active = False
    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    return CategoryPublic.model_validate(categoria, from_attributes=True)


# --- productos --------------------------------------------------------------


@router.get("/products", dependencies=[Depends(requiere(P.CATALOG_READ))], summary="La carta")
def listar_productos(
    session: SessionDep,
    alcance: SucursalActiva,
    pagina: Paginacion,
    q: str | None = Query(default=None, max_length=80),
    categoria: UUID | None = None,
    incluir_inactivos: bool = False,
) -> Pagina[ProductPublic]:
    consulta = catalog_service.consulta_de_productos(alcance)

    if not incluir_inactivos:
        consulta = consulta.where(col(Product.is_active).is_(True))
    if categoria is not None:
        consulta = consulta.where(col(Product.category_id) == categoria)
    if q:
        # Busqueda simple por ahora. La version sin acentos, con la extension
        # `unaccent`, llega con su migracion.
        consulta = consulta.where(col(Product.name).ilike(f"%{q.strip()}%"))

    total = paginar(session, consulta.order_by(col(Product.name)), pagina)
    return Pagina[ProductPublic](
        items=[catalog_service.a_publico(f) for f in total.items],
        page=total.page,
        size=total.size,
        total=total.total,
        has_more=total.has_more,
    )


@router.post(
    "/products",
    status_code=201,
    dependencies=[Depends(requiere(P.CATALOG_WRITE))],
    summary="Crear producto",
)
def crear_producto(
    datos: ProductCreate, session: SessionDep, alcance: SucursalActiva
) -> ProductPublic:
    if datos.station not in ESTACIONES:
        raise NoEncontrado("Esa estacion no existe.")

    producto = Product.model_validate(datos)
    session.add(producto)
    session.commit()
    session.refresh(producto)

    fila = session.exec(
        catalog_service.consulta_de_productos(alcance).where(col(Product.id) == producto.id)
    ).one()
    return catalog_service.a_publico(fila)


@router.patch(
    "/products/{producto_id}",
    dependencies=[Depends(requiere(P.CATALOG_WRITE))],
    summary="Editar producto",
)
def editar_producto(
    producto_id: UUID, datos: ProductUpdate, session: SessionDep, alcance: SucursalActiva
) -> ProductPublic:
    producto = session.get(Product, producto_id)
    if producto is None:
        raise NoEncontrado("Ese producto no existe.")

    cambios = datos.model_dump(exclude_unset=True)
    if "station" in cambios and cambios["station"] not in ESTACIONES:
        raise NoEncontrado("Esa estacion no existe.")

    for campo, valor in cambios.items():
        setattr(producto, campo, valor)
    session.add(producto)
    session.commit()

    fila = session.exec(
        catalog_service.consulta_de_productos(alcance).where(col(Product.id) == producto_id)
    ).one()
    return catalog_service.a_publico(fila)


@router.put(
    "/products/{producto_id}/branch",
    dependencies=[Depends(requiere(P.CATALOG_WRITE))],
    summary="Precio y disponibilidad EN ESTA SUCURSAL",
)
def ajustar_en_sucursal(
    producto_id: UUID,
    datos: ProductBranchUpdate,
    session: SessionDep,
    alcance: SucursalActiva,
) -> ProductPublic:
    """
    El override de una sede.

    La fila se crea al vuelo la primera vez que hay algo que decir. No se siembra
    al dar de alta la sucursal: con cuatro sedes y trescientos productos eso son
    mil doscientas filas que solo sirven para repetir el precio base.
    """
    if alcance.consolidado:
        from app.core.errors import ErrorAplicacion

        raise ErrorAplicacion(
            400, "escritura_sin_sucursal", "Elige una sucursal para ajustar el precio."
        )

    if session.get(Product, producto_id) is None:
        raise NoEncontrado("Ese producto no existe.")

    override = session.get(ProductBranch, (producto_id, alcance.branch_id))
    if override is None:
        override = ProductBranch(product_id=producto_id, branch_id=alcance.branch_id)

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(override, campo, valor)
    session.add(override)
    session.commit()

    fila = session.exec(
        catalog_service.consulta_de_productos(alcance).where(col(Product.id) == producto_id)
    ).one()
    return catalog_service.a_publico(fila)


@router.delete(
    "/products/{producto_id}",
    dependencies=[Depends(requiere(P.CATALOG_WRITE))],
    summary="Retirar producto",
)
def retirar_producto(
    producto_id: UUID, session: SessionDep, alcance: SucursalActiva
) -> ProductPublic:
    producto = session.get(Product, producto_id)
    if producto is None:
        raise NoEncontrado("Ese producto no existe.")

    # Baja logica: ver el comentario de las categorias.
    producto.is_active = False
    session.add(producto)
    session.commit()

    fila = session.exec(
        catalog_service.consulta_de_productos(alcance).where(col(Product.id) == producto_id)
    ).one()
    return catalog_service.a_publico(fila)
