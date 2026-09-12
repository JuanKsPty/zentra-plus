from uuid import UUID

from fastapi import APIRouter, Depends

from app.core import permissions as P
from app.core.deps import SesionActual, SessionDep, SucursalActiva, requiere
from app.core.errors import Conflicto
from app.domain.arqueo import ETIQUETAS_DE_METODO
from app.models import (
    AbrirTurno,
    ArqueoPublic,
    CerrarTurno,
    CobroNuevo,
    EstadoDeCobro,
    PaymentPublic,
    PropinaNueva,
    ShiftPublic,
    VentaDeMostrador,
)
from app.services import cash_service, counter_sale_service, order_service

router = APIRouter(tags=["caja"])


# --- turnos -----------------------------------------------------------------


@router.get(
    "/shifts/current",
    dependencies=[Depends(requiere(P.CASH_READ))],
    summary="Mi caja abierta",
)
def turno_actual(
    session: SessionDep, alcance: SucursalActiva, sesion: SesionActual
) -> ShiftPublic | None:
    """
    `null` cuando no hay ninguna abierta, y no un 404.

    «No tienes caja abierta» es un estado normal de la pantalla —el primero del
    dia— no un error que haya que manejar aparte.
    """
    turno = cash_service.turno_abierto(session, alcance, sesion.sub)
    return ShiftPublic.model_validate(turno, from_attributes=True) if turno else None


@router.post(
    "/shifts/open",
    status_code=201,
    dependencies=[Depends(requiere(P.CASH_WRITE))],
    summary="Abrir caja",
)
def abrir(
    datos: AbrirTurno, session: SessionDep, alcance: SucursalActiva, sesion: SesionActual
) -> ShiftPublic:
    turno = cash_service.abrir_turno(session, datos, alcance, sesion.sub)
    return ShiftPublic.model_validate(turno, from_attributes=True)


@router.get(
    "/shifts/{turno_id}/summary",
    dependencies=[Depends(requiere(P.CASH_READ))],
    summary="El arqueo",
)
def arqueo(turno_id: UUID, session: SessionDep, alcance: SucursalActiva) -> ArqueoPublic:
    turno = cash_service.obtener_turno(session, turno_id, alcance)
    return _arqueo_publico(turno, cash_service.arqueo_de(session, turno))


@router.post(
    "/shifts/{turno_id}/close",
    dependencies=[Depends(requiere(P.CASH_WRITE))],
    summary="Cerrar caja",
)
def cerrar(
    turno_id: UUID,
    datos: CerrarTurno,
    session: SessionDep,
    alcance: SucursalActiva,
    sesion: SesionActual,
) -> ArqueoPublic:
    turno = cash_service.obtener_turno(session, turno_id, alcance)
    if turno.opened_by != sesion.sub:
        # Cerrar la caja de otro deja su arqueo a nombre de quien no la conto.
        raise Conflicto("caja_ajena", "Esa caja la abrio otra persona.")

    turno, resultado = cash_service.cerrar_turno(session, turno, datos, sesion.sub)
    return _arqueo_publico(turno, resultado)


# --- cobro ------------------------------------------------------------------


@router.get(
    "/orders/{orden_id}/payments",
    dependencies=[Depends(requiere(P.CASH_READ))],
    summary="Lo cobrado y lo que falta",
)
def estado(orden_id: UUID, session: SessionDep, alcance: SucursalActiva) -> EstadoDeCobro:
    orden = order_service.obtener(session, orden_id, alcance)
    cobros, pagado, falta = cash_service.estado_de_cobro(session, orden)
    return EstadoDeCobro(
        order_id=orden.id,
        total=orden.total,
        paid=pagado,  # type: ignore[arg-type]
        due=falta,  # type: ignore[arg-type]
        is_settled=falta <= 0,  # type: ignore[operator]
        payments=[PaymentPublic.model_validate(c, from_attributes=True) for c in cobros],
    )


@router.post(
    "/orders/{orden_id}/payments",
    status_code=201,
    dependencies=[Depends(requiere(P.CASH_WRITE))],
    summary="Cobrar",
)
def cobrar(
    orden_id: UUID,
    datos: CobroNuevo,
    session: SessionDep,
    alcance: SucursalActiva,
    sesion: SesionActual,
) -> EstadoDeCobro:
    """
    Un cobro. Varios por cuenta: asi funciona pagar a medias.

    El IMPORTE viaja —pagar a medias es decidir cuanto pone cada uno— pero el
    TOTAL de la cuenta no: ese lo sabe el servidor, con el precio de la
    sucursal. Un total que viene del cliente es un total calculado con un precio
    que puede estar viejo.
    """
    orden = order_service.obtener(session, orden_id, alcance)
    cash_service.cobrar(session, orden, datos, alcance, sesion.sub)
    return estado(orden_id, session, alcance)


@router.patch(
    "/orders/{orden_id}/tip",
    dependencies=[Depends(requiere(P.CASH_WRITE))],
    summary="Poner propina",
)
def propina(
    orden_id: UUID, datos: PropinaNueva, session: SessionDep, alcance: SucursalActiva
) -> EstadoDeCobro:
    orden = order_service.obtener(session, orden_id, alcance)
    cash_service.poner_propina(session, orden, datos.tip_amount)
    return estado(orden_id, session, alcance)


# --- ayudas -----------------------------------------------------------------


def _arqueo_publico(turno, resultado) -> ArqueoPublic:
    return ArqueoPublic(
        shift=ShiftPublic.model_validate(turno, from_attributes=True),
        by_method=resultado.por_metodo,
        total_sold=resultado.total_vendido,
        cash_sold=resultado.efectivo_vendido,
        expected_cash=resultado.efectivo_esperado,
        counted_cash=resultado.efectivo_contado,
        difference=resultado.diferencia,
        payments_count=resultado.cuantos_cobros,
    )


@router.post(
    "/counter-sales",
    status_code=201,
    dependencies=[Depends(requiere(P.ORDERS_WRITE, P.CASH_WRITE))],
    summary="Venta de mostrador",
)
def venta_de_mostrador(
    datos: VentaDeMostrador,
    session: SessionDep,
    alcance: SucursalActiva,
    sesion: SesionActual,
) -> EstadoDeCobro:
    """
    Crear, cobrar y cerrar en UNA peticion.

    Exige los DOS permisos: quien vende en mostrador esta tomando una comanda y
    cobrandola a la vez. Con uno solo se podria hacer media operacion, que es
    justo la que no existe.
    """
    orden = counter_sale_service.vender(session, datos, alcance, sesion.sub)
    return estado(orden.id, session, alcance)


@router.get(
    "/payment-methods",
    dependencies=[Depends(requiere(P.CASH_READ))],
    summary="Como se puede cobrar",
)
def metodos() -> dict[str, str]:
    """
    Las etiquetas salen de la API y no del frontend.

    Es vocabulario del dominio: si manana se anade un metodo, la pantalla de
    caja se entera sola en vez de esperar a que alguien actualice una lista
    paralela.
    """
    return ETIQUETAS_DE_METODO
