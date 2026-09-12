"""
La venta de mostrador: crear, cobrar y cerrar en un solo acto.
"""

from uuid import UUID

from sqlmodel import Session

from app.core.errors import Conflicto
from app.core.occurred_at import resolver
from app.db.scoping import Alcance
from app.domain.arqueo import METODOS
from app.domain.order_totals import totales
from app.models import CobroNuevo, Order, OrderStatusHistory, VentaDeMostrador
from app.realtime.events import sobre
from app.realtime.hub import hub
from app.services import cash_service, order_service
from app.services.numbering import siguiente_numero


def vender(session: Session, datos: VentaDeMostrador, alcance: Alcance, cajero: UUID) -> Order:
    """
    Una sola peticion. NO dos.

    Si fueran dos —crear y luego cobrar— un telefono con datos flojos dejaria la
    comanda creada y el cobro no: una cuenta de mostrador abierta, sin mesa y
    sin nadie mirandola, engordando «por cobrar» hasta que alguien la cancele a
    mano. Y el cajero no tiene forma de saber si tiene que reintentar.

    REENVIAR NO DUPLICA: el identificador lo acuna el dispositivo, igual que en
    una comanda normal.
    """
    if datos.id is not None:
        existente = session.get(Order, datos.id)
        if existente is not None:
            if existente.branch_id != alcance.branch_id:
                from app.core.errors import NoEncontrado

                raise NoEncontrado("Esa venta no existe.")
            return existente

    if datos.method not in METODOS:
        from app.core.errors import ErrorAplicacion

        raise ErrorAplicacion(422, "metodo_invalido", "Ese metodo de cobro no existe.")

    # EL TURNO SE COMPRUEBA ANTES DE CREAR NADA, aunque el servicio de cobro lo
    # vuelva a mirar. Parece redundante y no lo es: si se dejara solo alli, la
    # comanda ya existiria cuando salta el error, y quedaria una venta de
    # mostrador abierta que nadie va a cerrar. El fallo mas probable de este
    # endpoint es el primer uso del dia, justo cuando no hay caja abierta.
    turno = cash_service.turno_abierto(session, alcance, cajero)
    if turno is None:
        raise Conflicto(
            "sin_turno", "Abre tu caja antes de vender: el cobro tiene que ir a un turno."
        )

    ocurrido = resolver(datos.occurred_at)
    lineas = [order_service._linea(session, item, alcance) for item in datos.items]

    # El total se calcula ANTES de escribir. Una venta que suma cero —productos
    # a precio cero, o una lista que se quedo vacia por el camino— reventaria
    # al cobrar, con la comanda ya creada: justo la venta huerfana que este
    # endpoint existe para no dejar nunca.
    subtotal, total = totales(lineas)  # type: ignore[arg-type]
    if total <= 0:
        raise Conflicto(
            "venta_sin_importe",
            "Esa venta suma cero. Anade algo que cobrar antes de continuar.",
        )

    orden = Order(
        branch_id=alcance.branch_id,
        order_number=siguiente_numero(session, alcance.branch_id),
        label=datos.label or "Mostrador",
        # `counter` SOLO se escribe aqui. `POST /orders` no lo acepta: si lo
        # aceptara, cualquiera con permiso de comandas podria marcar una normal
        # como venta de mostrador y hacerla desaparecer del tablero de cocina
        # sin cobrarla.
        source="counter",
        status="pending",
        shift_id=turno.id,
        waiter_id=cajero,
        occurred_at=ocurrido,
    )
    if datos.id is not None:
        orden.id = datos.id

    session.add(orden)
    for linea in lineas:
        linea.order_id = orden.id
        session.add(linea)

    orden.subtotal, orden.total = subtotal, total
    session.add(
        OrderStatusHistory(
            order_id=orden.id, from_status=None, to_status="pending", occurred_at=ocurrido
        )
    )
    session.commit()
    session.refresh(orden)

    # El cobro, con la misma clave de reenvio que trajo la venta: si el cliente
    # reintenta la venta entera, ni la comanda ni el cobro se duplican.
    cash_service.cobrar(
        session,
        orden,
        CobroNuevo(
            method=datos.method,
            amount=orden.total,
            client_request_id=datos.client_request_id,
            occurred_at=datos.occurred_at,
        ),
        alcance,
        cajero,
    )
    session.refresh(orden)

    hub.publicar_desde_hilo(
        sobre(
            "order.changed",
            orden.branch_id,
            orderId=str(orden.id),
            orderNumber=orden.order_number,
            status=orden.status,
            tableId=None,
        )
    )
    return orden
