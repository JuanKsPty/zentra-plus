from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import col

from app.core import permissions as P
from app.core.deps import SesionActual, SessionDep, SucursalActiva, requiere
from app.core.pagination import Pagina, Paginacion, paginar
from app.db.scoping import consulta
from app.domain import order_state
from app.models import (
    CambioDeEstado,
    LineaAnadida,
    OrdenNueva,
    Order,
    OrderItemPublic,
    OrderPublic,
    RestaurantTable,
)
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["comandas"])


def _publica(session: SessionDep, orden: Order) -> OrderPublic:
    lineas = order_service.lineas_de(session, orden.id)
    mesa = session.get(RestaurantTable, orden.table_id) if orden.table_id else None
    return OrderPublic(
        id=orden.id,
        order_number=orden.order_number,
        label=orden.label,
        table_id=orden.table_id,
        table_number=mesa.number if mesa else None,
        waiter_id=orden.waiter_id,
        source=orden.source,
        status=orden.status,
        notes=orden.notes,
        subtotal=orden.subtotal,
        tip_amount=orden.tip_amount,
        total=orden.total,
        # Se lee siempre asi: la hora del hecho si la hay, la de llegada si no.
        occurred_at=orden.occurred_at or orden.created_at,
        created_at=orden.created_at,
        items=[OrderItemPublic.model_validate(x, from_attributes=True) for x in lineas],
    )


@router.get("", dependencies=[Depends(requiere(P.ORDERS_READ))], summary="Las comandas")
def listar(
    session: SessionDep,
    alcance: SucursalActiva,
    pagina: Paginacion,
    abiertas: bool = Query(default=False, description="Solo las que siguen vivas en el salon"),
    mesa: UUID | None = None,
    estado: str | None = None,
) -> Pagina[OrderPublic]:
    q = consulta(Order, alcance)

    if abiertas:
        q = q.where(col(Order.status).in_(order_state.ABIERTAS))
    if estado:
        q = q.where(col(Order.status) == estado)
    if mesa is not None:
        q = q.where(col(Order.table_id) == mesa)

    pagina_cruda = paginar(session, q.order_by(col(Order.created_at).desc()), pagina)
    return Pagina[OrderPublic](
        items=[_publica(session, o) for o in pagina_cruda.items],
        page=pagina_cruda.page,
        size=pagina_cruda.size,
        total=pagina_cruda.total,
        has_more=pagina_cruda.has_more,
    )


# Ruta literal ANTES del comodin: en Starlette gana la primera que casa, y si
# estuviera despues se intentaria leer «kds» como un identificador.
@router.get("/kds", dependencies=[Depends(requiere(P.ORDERS_READ))], summary="El tablero de cocina")
def tablero(
    session: SessionDep,
    alcance: SucursalActiva,
    estacion: str | None = Query(default=None, description="kitchen, bar o immediate"),
) -> list[OrderPublic]:
    """
    Lo que la cocina tiene que atender.

    Ordenado por la hora del HECHO y no por la de llegada: una comanda que se
    escribio hace diez minutos y llego ahora tiene que ponerse en su sitio de la
    cola, no al final. Es lo que hace que el tablero siga siendo justo cuando
    una tableta se queda sin red un rato.
    """
    q = (
        consulta(Order, alcance)
        .where(col(Order.status).in_(order_state.EN_COCINA))
        .order_by(col(Order.occurred_at).asc(), col(Order.created_at).asc())
    )
    ordenes = session.exec(q).all()

    publicas = [_publica(session, o) for o in ordenes]
    if estacion:
        publicas = [
            o.model_copy(update={"items": [x for x in o.items if x.station == estacion]})
            for o in publicas
        ]
        # Una comanda cuyas lineas son todas de otra estacion no pinta nada en
        # este tablero: ensenarla vacia solo estorba.
        publicas = [o for o in publicas if o.items]
    return publicas


@router.post(
    "",
    status_code=201,
    dependencies=[Depends(requiere(P.ORDERS_WRITE))],
    summary="Tomar una comanda",
)
def crear(
    datos: OrdenNueva, session: SessionDep, alcance: SucursalActiva, sesion: SesionActual
) -> OrderPublic:
    """
    El `id` lo puede acunar el dispositivo, y reenviar con el mismo NO duplica.

    `source` no se acepta en el cuerpo. Si se pudiera pedir, cualquiera con
    permiso de comandas podria marcar una como venta de mostrador y hacerla
    desaparecer del tablero de cocina sin cobrarla.
    """
    orden, _era_nueva = order_service.crear(session, datos, alcance, waiter_id=sesion.sub)
    return _publica(session, orden)


@router.get("/{orden_id}", dependencies=[Depends(requiere(P.ORDERS_READ))], summary="Una comanda")
def ver(orden_id: UUID, session: SessionDep, alcance: SucursalActiva) -> OrderPublic:
    return _publica(session, order_service.obtener(session, orden_id, alcance))


@router.post(
    "/{orden_id}/items",
    status_code=201,
    dependencies=[Depends(requiere(P.ORDERS_WRITE))],
    summary="Anadir una linea",
)
def anadir(
    orden_id: UUID, datos: LineaAnadida, session: SessionDep, alcance: SucursalActiva
) -> OrderPublic:
    orden = order_service.obtener(session, orden_id, alcance)
    order_service.anadir_linea(session, orden, datos, alcance)
    session.refresh(orden)
    return _publica(session, orden)


@router.patch(
    "/{orden_id}/status",
    dependencies=[Depends(requiere(P.ORDERS_WRITE))],
    summary="Mover el estado",
)
def mover(
    orden_id: UUID,
    datos: CambioDeEstado,
    session: SessionDep,
    alcance: SucursalActiva,
    sesion: SesionActual,
) -> OrderPublic:
    orden = order_service.obtener(session, orden_id, alcance)
    order_service.cambiar_estado(
        session, orden, datos.status, por=sesion.sub, ocurrido_en=datos.occurred_at
    )
    return _publica(session, orden)


@router.patch(
    "/{orden_id}/bump",
    dependencies=[Depends(requiere(P.ORDERS_BUMP))],
    summary="Avanzar desde cocina",
)
def avanzar_desde_cocina(
    orden_id: UUID,
    datos: CambioDeEstado,
    session: SessionDep,
    alcance: SucursalActiva,
    sesion: SesionActual,
) -> OrderPublic:
    """
    Lo que la cocina puede hacer: marcar «en preparacion» y «lista».

    Permiso propio, y no `orders:write`. Avanzar el estado no es lo mismo que
    editar una comanda: la cocina no anade lineas ni cambia cantidades, y darle
    el permiso ancho para que pueda tocar un boton es como se acaba con un
    tablero que puede modificar la cuenta.
    """
    if datos.status not in ("preparing", "ready"):
        from app.core.errors import ErrorAplicacion

        raise ErrorAplicacion(
            403,
            "sin_permiso",
            "Desde cocina solo se puede marcar «en preparacion» o «lista».",
        )

    orden = order_service.obtener(session, orden_id, alcance)
    order_service.cambiar_estado(
        session, orden, datos.status, por=sesion.sub, ocurrido_en=datos.occurred_at
    )
    return _publica(session, orden)
