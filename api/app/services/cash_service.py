"""
Turnos de caja y cobro.

Es el modulo donde un error cuesta dinero, asi que casi cada decision de aqui
tiene su comentario.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col

from app.core.conflicts import traducir
from app.core.errors import Conflicto, ErrorAplicacion, NoEncontrado
from app.core.occurred_at import resolver
from app.db.scoping import Alcance, consulta, crear_en_sucursal
from app.domain import order_state
from app.domain.arqueo import METODOS, Arqueo, arquear
from app.domain.order_totals import cuantizar, esta_saldada, falta_por_cobrar, totales
from app.models import (
    AbrirTurno,
    CerrarTurno,
    CobroNuevo,
    Order,
    OrderStatusHistory,
    Payment,
    RestaurantTable,
    Shift,
)
from app.realtime.events import sobre
from app.realtime.hub import hub
from app.services import order_service

# --- turnos -----------------------------------------------------------------


def turno_abierto(session: Session, alcance: Alcance, cajero: UUID) -> Shift | None:
    return session.exec(
        consulta(Shift, alcance)
        .where(col(Shift.opened_by) == cajero)
        .where(col(Shift.status) == "open")
    ).first()


def abrir_turno(session: Session, datos: AbrirTurno, alcance: Alcance, cajero: UUID) -> Shift:
    if (ya := turno_abierto(session, alcance, cajero)) is not None:
        # La comprobacion previa da el mensaje bueno en el caso normal. El
        # indice parcial cierra la ventana que deja abierta.
        raise Conflicto(
            "turno_ya_abierto",
            f"Ya tienes una caja abierta desde las {ya.opened_at.astimezone().strftime('%H:%M')}.",
        )

    turno = crear_en_sucursal(Shift, datos, alcance, opened_by=cajero, status="open")
    session.add(turno)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        # El doble clic. Sin traducirlo saldria como 500, y un 500 aqui hace que
        # el cajero lo intente otra vez — que es exactamente lo que no conviene.
        codigo, mensaje = traducir(
            error,
            {
                "idx_shifts_un_abierto_por_cajero_y_sucursal": (
                    "turno_ya_abierto",
                    "Ya tienes una caja abierta.",
                )
            },
            por_defecto=("turno_ya_abierto", "Ya tienes una caja abierta."),
        )
        raise Conflicto(codigo, mensaje) from error

    session.refresh(turno)
    _avisar_turno(turno)
    return turno


def cerrar_turno(
    session: Session, turno: Shift, datos: CerrarTurno, cajero: UUID
) -> tuple[Shift, Arqueo]:
    if turno.status != "open":
        raise Conflicto("turno_cerrado", "Esa caja ya esta cerrada.")

    pendientes = session.exec(
        consulta(Order, Alcance.de(turno.branch_id))
        .where(col(Order.shift_id) == turno.id)
        .where(col(Order.status).in_(order_state.ABIERTAS))
    ).all()
    if pendientes:
        # Cerrar con cuentas vivas dejaria cobros de este turno cayendo en el
        # siguiente, y entonces no cuadra ninguno de los dos.
        numeros = ", ".join(f"#{o.order_number}" for o in pendientes[:5])
        raise Conflicto(
            "cuentas_abiertas",
            f"Quedan {len(pendientes)} cuentas sin cerrar ({numeros}). "
            "Cobralas o anulalas antes de cerrar la caja.",
        )

    turno.closing_cash = datos.closing_cash
    turno.closed_by = cajero
    turno.closed_at = datetime.now(UTC)
    turno.status = "closed"
    if datos.notes:
        turno.notes = datos.notes

    session.add(turno)
    session.commit()
    session.refresh(turno)

    _avisar_turno(turno)
    return turno, arqueo_de(session, turno)


def arqueo_de(session: Session, turno: Shift) -> Arqueo:
    # El alcance se deriva del propio turno: aqui ya se sabe de que sucursal es.
    cobros = session.exec(
        consulta(Payment, Alcance.de(turno.branch_id)).where(col(Payment.shift_id) == turno.id)
    ).all()
    return arquear(list(cobros), turno.opening_cash, turno.closing_cash)


# --- cobro ------------------------------------------------------------------


def estado_de_cobro(session: Session, orden: Order) -> tuple[list[Payment], object, object]:
    cobros = list(
        session.exec(
            consulta(Payment, Alcance.de(orden.branch_id))
            .where(col(Payment.order_id) == orden.id)
            .order_by(col(Payment.processed_at))
        ).all()
    )
    pagado = cuantizar(sum((c.amount for c in cobros), start=orden.total * 0))
    return cobros, pagado, falta_por_cobrar(orden.total, pagado)


def cobrar(
    session: Session,
    orden: Order,
    datos: CobroNuevo,
    alcance: Alcance,
    cajero: UUID,
) -> Payment:
    """
    Registra un cobro y, si salda la cuenta, la cierra y libera la mesa.

    EL ORDEN DE LAS COMPROBACIONES IMPORTA. La clave de reenvio se mira ANTES
    que cualquier otra cosa: el cobro original pudo cerrar la cuenta, asi que un
    reintento chocaria contra «esta cuenta ya esta cerrada» — un fallo FALSO que
    dejaria la cola reintentando algo que ya se aplico.
    """
    if datos.client_request_id:
        # Filtrada por sucursal aunque la clave sea unica en toda la base: si
        # alguna vez llegara una de otra sede, devolver SU cobro seria una fuga
        # — y responder con un importe ajeno es la peor forma de tenerla.
        ya = session.exec(
            consulta(Payment, alcance).where(
                col(Payment.client_request_id) == datos.client_request_id
            )
        ).first()
        if ya is not None:
            return ya

    if datos.method not in METODOS:
        raise ErrorAplicacion(422, "metodo_invalido", "Ese metodo de cobro no existe.")

    if orden.status == "cancelled":
        raise Conflicto("comanda_anulada", "Esa cuenta esta anulada: no se puede cobrar.")

    turno = turno_abierto(session, alcance, cajero)
    if turno is None:
        # Antes de escribir nada. Sin turno, el cobro no tendria a que arqueo
        # pertenecer y aparecerian ingresos que ninguna caja explica.
        raise Conflicto(
            "sin_turno", "Abre tu caja antes de cobrar: el cobro tiene que ir a un turno."
        )

    _, pagado, falta = estado_de_cobro(session, orden)
    if falta <= 0:
        raise Conflicto("cuenta_saldada", "Esa cuenta ya esta pagada.")

    cobro = crear_en_sucursal(
        Payment,
        {
            "method": datos.method,
            "amount": datos.amount,
            "reference": datos.reference,
            "client_request_id": datos.client_request_id,
        },
        alcance,
        order_id=orden.id,
        shift_id=turno.id,
        processed_by=cajero,
        occurred_at=resolver(datos.occurred_at),
    )
    session.add(cobro)

    # El turno se SELLA en el cobro, no se deduce despues por rango de fechas:
    # derivarlo por fechas deja fuera los cobros de la medianoche, que son justo
    # los que cambian de turno.
    orden.shift_id = turno.id

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # Dos reenvios a la vez: los dos pasaron la comprobacion previa. La
        # respuesta correcta es el cobro que gano, no un error.
        if datos.client_request_id:
            ganador = session.exec(
                consulta(Payment, alcance).where(
                    col(Payment.client_request_id) == datos.client_request_id
                )
            ).first()
            if ganador is not None:
                return ganador
        raise

    session.refresh(cobro)
    session.refresh(orden)

    _, _, queda = estado_de_cobro(session, orden)
    if queda <= 0:
        _cerrar_por_cobro(session, orden, cajero)

    order_service.lineas_de(session, orden.id)
    hub.publicar_desde_hilo(
        sobre(
            "order.changed",
            orden.branch_id,
            orderId=str(orden.id),
            orderNumber=orden.order_number,
            status=orden.status,
            tableId=str(orden.table_id) if orden.table_id else None,
        )
    )
    return cobro


def poner_propina(session: Session, orden: Order, propina) -> Order:
    if order_state.es_terminal(orden.status):
        raise Conflicto(
            "comanda_cerrada", "Esa cuenta ya esta cerrada: la propina se pone antes de cobrar."
        )

    orden.tip_amount = propina
    orden.subtotal, orden.total = totales(
        order_service.lineas_de(session, orden.id),  # type: ignore[arg-type]
        propina,
    )
    session.add(orden)
    session.commit()
    session.refresh(orden)
    return orden


def _cerrar_por_cobro(session: Session, orden: Order, cajero: UUID) -> None:
    """
    El unico camino legitimo para cerrar una cuenta.

    Se salta la maquina de estados a proposito: `cambiar_estado` rechaza
    `closed` SIEMPRE, para que ninguna pantalla pueda cerrar una cuenta sin
    cobrarla. Aqui ya se sabe que esta saldada.
    """
    anterior = orden.status
    orden.status = "closed"
    session.add(orden)
    session.add(
        OrderStatusHistory(
            order_id=orden.id,
            from_status=anterior,
            to_status="closed",
            changed_by=cajero,
            occurred_at=datetime.now(UTC),
        )
    )

    if orden.table_id is not None:
        mesa = session.get(RestaurantTable, orden.table_id)
        otras = session.exec(
            consulta(Order, Alcance.de(orden.branch_id))
            .where(col(Order.table_id) == orden.table_id)
            .where(col(Order.id) != orden.id)
            .where(col(Order.status).in_(order_state.ABIERTAS))
        ).first()
        if mesa is not None and otras is None:
            # A «por recoger», no a «libre». Una mesa recien cobrada no esta
            # lista: hay que recogerla, y si el sistema dice que esta libre el
            # anfitrion sienta a alguien encima de los platos del anterior.
            mesa.status = "cleaning"
            mesa.status_changed_at = datetime.now(UTC)
            session.add(mesa)
            hub.publicar_desde_hilo(
                sobre(
                    "table.changed",
                    mesa.branch_id,
                    tableId=str(mesa.id),
                    number=mesa.number,
                    status=mesa.status,
                )
            )

    session.commit()


def _avisar_turno(turno: Shift) -> None:
    hub.publicar_desde_hilo(
        sobre("shift.changed", turno.branch_id, shiftId=str(turno.id), status=turno.status)
    )


def obtener_turno(session: Session, turno_id: UUID, alcance: Alcance) -> Shift:
    turno = session.exec(consulta(Shift, alcance).where(col(Shift.id) == turno_id)).first()
    if turno is None:
        raise NoEncontrado("Ese turno no existe.")
    return turno


def esta_saldada_la_cuenta(total, pagado) -> bool:
    return esta_saldada(total, pagado)
