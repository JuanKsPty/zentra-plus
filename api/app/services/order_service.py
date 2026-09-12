"""
Comandas: crearlas, anadirles lineas y moverles el estado.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.conflicts import es_conflicto_concurrente
from app.core.errors import Conflicto, ErrorAplicacion, NoEncontrado
from app.core.occurred_at import resolver
from app.db.scoping import Alcance, consulta
from app.domain import order_state
from app.domain.order_totals import subtotal_de_linea, totales
from app.models import (
    LineaAnadida,
    LineaNueva,
    OrdenNueva,
    Order,
    OrderItem,
    OrderStatusHistory,
    Product,
    RestaurantTable,
)
from app.realtime.events import sobre
from app.realtime.hub import hub
from app.services import catalog_service
from app.services.numbering import siguiente_numero


def obtener(session: Session, orden_id: UUID, alcance: Alcance) -> Order:
    orden = session.exec(consulta(Order, alcance).where(col(Order.id) == orden_id)).first()
    if orden is None:
        # 404 y no 403: un 403 confirmaria que esa comanda existe en otra sede.
        raise NoEncontrado("Esa comanda no existe.")
    return orden


def lineas_de(session: Session, orden_id: UUID) -> list[OrderItem]:
    return list(
        session.exec(
            select(OrderItem)
            .where(col(OrderItem.order_id) == orden_id)
            .order_by(col(OrderItem.created_at))
        ).all()
    )


def crear(
    session: Session,
    datos: OrdenNueva,
    alcance: Alcance,
    *,
    waiter_id: UUID | None,
) -> tuple[Order, bool]:
    """
    Devuelve (comanda, era_nueva).

    IDEMPOTENCIA: LEER ANTES DE ESCRIBIR. Si el dispositivo acuno el id y ya
    existe una comanda con el, se devuelve TAL CUAL — sin volver a ocupar la
    mesa, sin volver a avisar a cocina y sin gastar otro numero de cuenta.

    Nunca `session.merge()`: con una clave primaria existente hace UPDATE y
    sobreescribe con los valores del objeto entrante, incluidos los nulos de los
    campos que no se rellenaron. Con borrado de huerfanos, ademas, se llevaria
    por delante las lineas anadidas despues.
    """
    if datos.id is not None:
        existente = session.get(Order, datos.id)
        if existente is not None:
            if existente.branch_id != alcance.branch_id:
                raise NoEncontrado("Esa comanda no existe.")
            return existente, False

    if alcance.consolidado:
        raise ErrorAplicacion(
            400, "escritura_sin_sucursal", "Elige una sucursal para tomar la comanda."
        )

    mesa = _mesa_valida(session, datos.table_id, alcance)
    ocurrido = resolver(datos.occurred_at)

    # Se resuelven los productos ANTES de pedir el numero: el numero bloquea la
    # fila contador de la sucursal hasta el commit, y validar el catalogo con el
    # cerrojo tomado encolaria a las demas comandas mientras tanto.
    lineas = [_linea(session, item, alcance) for item in datos.items]

    # Ojo: NO se pasa `id=None` cuando el dispositivo no lo acuno. Pasarlo
    # explicitamente ANULA el `default_factory` del modelo y el identificador se
    # queda en None hasta el flush — que es tarde, porque las lineas lo
    # necesitan antes para colgarse de la comanda.
    orden = Order(
        branch_id=alcance.branch_id,
        order_number=siguiente_numero(session, alcance.branch_id),
        table_id=mesa.id if mesa else None,
        label=datos.label,
        waiter_id=waiter_id,
        source="staff",
        status="pending",
        notes=datos.notes,
        occurred_at=ocurrido,
    )
    if datos.id is not None:
        orden.id = datos.id

    session.add(orden)
    for linea in lineas:
        linea.order_id = orden.id
        session.add(linea)

    _recalcular(orden, lineas)
    session.add(
        OrderStatusHistory(
            order_id=orden.id, from_status=None, to_status="pending", occurred_at=ocurrido
        )
    )

    if mesa is not None and mesa.status == "available":
        mesa.status = "occupied"
        mesa.status_changed_at = ocurrido
        session.add(mesa)

    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        # Dos reenvios simultaneos: los dos comprobaron antes de que existiera.
        # La respuesta correcta es la comanda que acaba de crear el otro, no un
        # error — y menos un 500, que para una cola de reenvios es definitivo.
        if datos.id is not None and es_conflicto_concurrente(error):
            ganadora = session.get(Order, datos.id)
            if ganadora is not None:
                return ganadora, False
        raise

    session.refresh(orden)

    # DESPUES del commit, nunca dentro de la transaccion: si abortara, la cocina
    # ya habria visto una comanda que no existe.
    _avisar(orden, "order.created")
    if mesa is not None:
        _avisar_mesa(mesa)

    return orden, True


def anadir_linea(
    session: Session, orden: Order, datos: LineaAnadida, alcance: Alcance
) -> OrderItem:
    if order_state.es_terminal(orden.status):
        raise Conflicto(
            "comanda_cerrada",
            f"Una comanda {order_state.ETIQUETAS[orden.status].lower()} ya no admite lineas.",
        )

    if datos.id is not None and (ya := session.get(OrderItem, datos.id)) is not None:
        # Reenvio de la misma linea. Igual que con la comanda: leer antes de
        # escribir, y devolver lo que hay.
        return ya

    linea = _linea(session, datos, alcance)
    linea.order_id = orden.id
    if datos.id is not None:
        linea.id = datos.id
    session.add(linea)
    session.commit()

    _recalcular(orden, lineas_de(session, orden.id))
    session.add(orden)
    session.commit()
    session.refresh(linea)
    _avisar(orden, "order.changed")
    return linea


def cambiar_estado(
    session: Session,
    orden: Order,
    nuevo: str,
    *,
    por: UUID | None,
    ocurrido_en: datetime | None = None,
) -> Order:
    motivo = order_state.motivo_si_no_puede(orden.status, nuevo)
    if motivo is not None:
        raise Conflicto("transicion_invalida", motivo)

    if orden.status == nuevo:
        # Marcar «lista» dos veces no puede fallar: el tablero se toca con prisa
        # y una comanda ya marcada no es un error, es un doble toque.
        return orden

    if nuevo == "closed":
        # Cerrar una cuenta es COBRARLA, y eso pasa por el servicio de cobro.
        # Dejarlo abierto aqui es el agujero de dinero mas facil de abrir: la
        # cuenta sale de «por cobrar» y la mesa se libera sin que entre nada.
        raise Conflicto(
            "cierre_sin_cobro",
            "Una cuenta se cierra al cobrarla, no cambiando su estado.",
        )

    anterior = orden.status
    ocurrido = resolver(ocurrido_en)
    orden.status = nuevo
    session.add(orden)
    session.add(
        OrderStatusHistory(
            order_id=orden.id,
            from_status=anterior,
            to_status=nuevo,
            changed_by=por,
            occurred_at=ocurrido,
        )
    )

    if nuevo == "cancelled" and orden.table_id is not None:
        mesa = session.get(RestaurantTable, orden.table_id)
        if mesa is not None and not _tiene_otras_vivas(session, orden):
            mesa.status = "available"
            mesa.status_changed_at = ocurrido
            session.add(mesa)

    session.commit()
    session.refresh(orden)

    _avisar(orden, "order.changed")
    if nuevo == "cancelled" and orden.table_id is not None:
        mesa = session.get(RestaurantTable, orden.table_id)
        if mesa is not None:
            _avisar_mesa(mesa)

    return orden


# --- avisos -----------------------------------------------------------------


def _avisar(orden: Order, tipo: str) -> None:
    """
    El evento lleva lo justo para que el cliente sepa QUE mirar.

    No lleva la comanda entera a proposito: es una senal, no un canal de datos.
    Asi un evento perdido por una reconexion no pierde nada — el estado sigue en
    la base y el cliente vuelve a pedirlo.
    """
    hub.publicar_desde_hilo(
        sobre(
            tipo,  # type: ignore[arg-type]
            orden.branch_id,
            orderId=str(orden.id),
            orderNumber=orden.order_number,
            status=orden.status,
            tableId=str(orden.table_id) if orden.table_id else None,
        )
    )


def _avisar_mesa(mesa: RestaurantTable) -> None:
    hub.publicar_desde_hilo(
        sobre(
            "table.changed",
            mesa.branch_id,
            tableId=str(mesa.id),
            number=mesa.number,
            status=mesa.status,
        )
    )


# --- ayudas -----------------------------------------------------------------


def _tiene_otras_vivas(session: Session, orden: Order) -> bool:
    """
    Si la mesa sigue teniendo alguna cuenta viva.

    El alcance se deriva de la propia comanda y no de la peticion: aqui ya se
    sabe a que sucursal pertenece, y construirlo asi mantiene el filtro en el
    unico sitio que lo sabe poner. Sin el, una mesa con el mismo identificador
    en otra sede —imposible hoy, pero el filtro no puede depender de eso—
    contaria como cuenta viva.
    """
    otras = session.exec(
        consulta(Order, Alcance.de(orden.branch_id))
        .where(col(Order.table_id) == orden.table_id)
        .where(col(Order.id) != orden.id)
        .where(col(Order.status).in_(order_state.ABIERTAS))
    ).first()
    return otras is not None


def _mesa_valida(
    session: Session, table_id: UUID | None, alcance: Alcance
) -> RestaurantTable | None:
    if table_id is None:
        return None
    mesa = session.exec(
        consulta(RestaurantTable, alcance).where(col(RestaurantTable.id) == table_id)
    ).first()
    if mesa is None:
        raise NoEncontrado("Esa mesa no existe.")
    if mesa.status == "maintenance":
        raise Conflicto("mesa_fuera_de_servicio", f"La mesa {mesa.number} esta fuera de servicio.")
    return mesa


def _linea(session: Session, datos: LineaNueva | LineaAnadida, alcance: Alcance) -> OrderItem:
    producto = session.get(Product, datos.product_id)
    if producto is None or not producto.is_active:
        raise NoEncontrado("Ese producto no esta en la carta.")

    precio = catalog_service.precio_efectivo(session, producto.id, alcance)

    return OrderItem(
        order_id=UUID(int=0),  # lo pone quien llama
        product_id=producto.id,
        # COPIAS, no referencias: renombrar un producto o cambiarle el precio
        # manana no puede reescribir un recibo ya impreso.
        product_name=producto.name,
        unit_price=precio,
        station=producto.station,
        quantity=datos.quantity,
        subtotal=subtotal_de_linea(datos.quantity, precio),
        notes=datos.notes,
        status="pending",
    )


def _recalcular(orden: Order, lineas: list[OrderItem]) -> None:
    orden.subtotal, orden.total = totales(lineas, orden.tip_amount)  # type: ignore[arg-type]
