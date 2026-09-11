from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlmodel import col

from app.core import permissions as P
from app.core.conflicts import traducir
from app.core.deps import SessionDep, SucursalActiva, requiere
from app.core.errors import Conflicto, ErrorAplicacion, NoEncontrado
from app.db.scoping import consulta, crear_en_sucursal
from app.models import (
    ESTADOS_DE_MESA,
    FORMAS_DE_MESA,
    RestaurantTable,
    Sector,
    SectorCreate,
    SectorPublic,
    SectorUpdate,
    TableCreate,
    TableLayoutUpdate,
    TablePublic,
    TableStatusUpdate,
    TableUpdate,
    ahora_utc,
)

router = APIRouter(prefix="/floor", tags=["salon"])


# --- sectores ---------------------------------------------------------------


@router.get("/sectors", dependencies=[Depends(requiere(P.FLOOR_READ))], summary="Las zonas")
def listar_sectores(session: SessionDep, alcance: SucursalActiva) -> list[SectorPublic]:
    filas = session.exec(
        consulta(Sector, alcance).order_by(col(Sector.sort_order), col(Sector.name))
    ).all()
    return [SectorPublic.model_validate(f, from_attributes=True) for f in filas]


@router.post(
    "/sectors",
    status_code=201,
    dependencies=[Depends(requiere(P.FLOOR_WRITE))],
    summary="Crear zona",
)
def crear_sector(datos: SectorCreate, session: SessionDep, alcance: SucursalActiva) -> SectorPublic:
    sector = crear_en_sucursal(Sector, datos, alcance)
    session.add(sector)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        # El indice unico cierra la ventana que dejaria un leer-antes-de-escribir,
        # y aqui se traduce al mismo error de negocio: una carrera entre dos
        # administradores no puede salir como un 500.
        codigo, mensaje = traducir(
            error,
            {
                "uq_sectors_nombre_por_sucursal": (
                    "zona_repetida",
                    f"Ya hay una zona llamada «{datos.name}» en esta sucursal.",
                )
            },
            por_defecto=("zona_repetida", f"Ya hay una zona llamada «{datos.name}» aqui."),
        )
        raise Conflicto(codigo, mensaje) from error
    session.refresh(sector)
    return SectorPublic.model_validate(sector, from_attributes=True)


@router.patch(
    "/sectors/{sector_id}",
    dependencies=[Depends(requiere(P.FLOOR_WRITE))],
    summary="Editar zona",
)
def editar_sector(
    sector_id: UUID, datos: SectorUpdate, session: SessionDep, alcance: SucursalActiva
) -> SectorPublic:
    sector = _sector_de(session, sector_id, alcance)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(sector, campo, valor)
    session.add(sector)
    session.commit()
    session.refresh(sector)
    return SectorPublic.model_validate(sector, from_attributes=True)


# --- mesas ------------------------------------------------------------------


@router.get("/tables", dependencies=[Depends(requiere(P.FLOOR_READ))], summary="Las mesas")
def listar_mesas(
    session: SessionDep, alcance: SucursalActiva, sector: UUID | None = None
) -> list[TablePublic]:
    q = consulta(RestaurantTable, alcance).where(col(RestaurantTable.is_active).is_(True))
    if sector is not None:
        q = q.where(col(RestaurantTable.sector_id) == sector)
    filas = session.exec(q.order_by(col(RestaurantTable.number))).all()
    return [TablePublic.model_validate(f, from_attributes=True) for f in filas]


# OJO CON EL ORDEN: `layout` es una ruta literal y tiene que declararse ANTES
# que `/{mesa_id}`. En Starlette gana la primera que casa, igual que en Nest, y
# si estuviera despues se intentaria leer «layout» como un uuid.
@router.patch(
    "/tables/layout",
    dependencies=[Depends(requiere(P.FLOOR_WRITE))],
    summary="Guardar el mapa entero",
)
def guardar_mapa(
    datos: TableLayoutUpdate, session: SessionDep, alcance: SucursalActiva
) -> list[TablePublic]:
    """
    Todas las posiciones en una sola peticion.

    Arrastrar seis mesas y mandar seis PATCH deja el mapa a medias si la red se
    corta en la tercera, y el operario no tiene forma de saber cuales llegaron.
    """
    por_id = {m.id: m for m in session.exec(consulta(RestaurantTable, alcance)).all()}

    for posicion in datos.tables:
        mesa = por_id.get(posicion.id)
        # Una mesa de otra sucursal sencillamente no esta en el diccionario. No
        # es un error que haya que contar: es que no existe para esta peticion.
        if mesa is None:
            continue
        mesa.position_x = posicion.position_x
        mesa.position_y = posicion.position_y
        session.add(mesa)

    session.commit()
    return listar_mesas(session, alcance)


@router.post(
    "/tables",
    status_code=201,
    dependencies=[Depends(requiere(P.FLOOR_WRITE))],
    summary="Crear mesa",
)
def crear_mesa(datos: TableCreate, session: SessionDep, alcance: SucursalActiva) -> TablePublic:
    if datos.shape not in FORMAS_DE_MESA:
        raise ErrorAplicacion(422, "forma_invalida", "Esa forma de mesa no existe.")

    # Que el sector sea de esta sucursal: si no, se podria colgar una mesa de la
    # zona de otra sede mandando su uuid.
    _sector_de(session, datos.sector_id, alcance)

    mesa = crear_en_sucursal(RestaurantTable, datos, alcance)
    session.add(mesa)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        # La comprobacion previa seria un leer-antes-de-escribir con una ventana
        # abierta entre las dos. El indice unico la cierra, y aqui se traduce al
        # mismo error de negocio para que la carrera no salga como un 500.
        codigo, mensaje = traducir(
            error,
            {
                "uq_tables_numero_por_sucursal": (
                    "mesa_repetida",
                    f"Ya hay una mesa {datos.number} en esta sucursal.",
                )
            },
            por_defecto=("mesa_repetida", f"Ya hay una mesa {datos.number} en esta sucursal."),
        )
        raise Conflicto(codigo, mensaje) from error
    session.refresh(mesa)
    return TablePublic.model_validate(mesa, from_attributes=True)


@router.patch(
    "/tables/{mesa_id}", dependencies=[Depends(requiere(P.FLOOR_WRITE))], summary="Editar mesa"
)
def editar_mesa(
    mesa_id: UUID, datos: TableUpdate, session: SessionDep, alcance: SucursalActiva
) -> TablePublic:
    mesa = _mesa_de(session, mesa_id, alcance)
    cambios = datos.model_dump(exclude_unset=True)

    if "shape" in cambios and cambios["shape"] not in FORMAS_DE_MESA:
        raise ErrorAplicacion(422, "forma_invalida", "Esa forma de mesa no existe.")
    if "sector_id" in cambios:
        _sector_de(session, cambios["sector_id"], alcance)

    for campo, valor in cambios.items():
        setattr(mesa, campo, valor)
    session.add(mesa)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        codigo, mensaje = traducir(
            error,
            {
                "uq_tables_numero_por_sucursal": (
                    "mesa_repetida",
                    "Ya hay una mesa con ese numero aqui.",
                )
            },
            por_defecto=("mesa_repetida", "Ya hay una mesa con ese numero aqui."),
        )
        raise Conflicto(codigo, mensaje) from error
    session.refresh(mesa)
    return TablePublic.model_validate(mesa, from_attributes=True)


@router.patch(
    "/tables/{mesa_id}/status",
    dependencies=[Depends(requiere(P.FLOOR_WRITE))],
    summary="Cambiar el estado de una mesa",
)
def cambiar_estado(
    mesa_id: UUID, datos: TableStatusUpdate, session: SessionDep, alcance: SucursalActiva
) -> TablePublic:
    if datos.status not in ESTADOS_DE_MESA:
        raise ErrorAplicacion(422, "estado_invalido", "Ese estado de mesa no existe.")

    mesa = _mesa_de(session, mesa_id, alcance)
    if mesa.status != datos.status:
        mesa.status = datos.status
        # Solo al CAMBIAR de estado. Tocarla en cada peticion haria inutil el
        # desempate que esta marca existe para resolver.
        mesa.status_changed_at = ahora_utc()
        session.add(mesa)
        session.commit()
        session.refresh(mesa)
    return TablePublic.model_validate(mesa, from_attributes=True)


# --- ayudas -----------------------------------------------------------------


def _sector_de(session: SessionDep, sector_id: UUID, alcance) -> Sector:
    sector = session.exec(consulta(Sector, alcance).where(col(Sector.id) == sector_id)).first()
    if sector is None:
        # 404 y no 403: un 403 confirmaria que esa zona existe en otra sucursal.
        raise NoEncontrado("Esa zona no existe.")
    return sector


def _mesa_de(session: SessionDep, mesa_id: UUID, alcance) -> RestaurantTable:
    mesa = session.exec(
        consulta(RestaurantTable, alcance).where(col(RestaurantTable.id) == mesa_id)
    ).first()
    if mesa is None:
        raise NoEncontrado("Esa mesa no existe.")
    return mesa
