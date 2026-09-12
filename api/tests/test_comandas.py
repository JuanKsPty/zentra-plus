from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import permissions as P
from app.models import Branch, Category, Order, OrderStatusHistory, Product, RestaurantTable, Sector
from tests.factories import cookie_con, crear_sucursal

MESERO = [P.ORDERS_READ, P.ORDERS_WRITE, P.FLOOR_READ, P.CATALOG_READ]
COCINA = [P.ORDERS_READ, P.ORDERS_BUMP, P.CATALOG_READ]


@pytest.fixture(name="sede")
def sede_fixture(session: Session) -> Branch:
    return crear_sucursal(session)


@pytest.fixture(name="carta")
def carta_fixture(session: Session) -> dict[str, Product]:
    categoria = Category(name="Carta")
    session.add(categoria)
    session.commit()
    session.refresh(categoria)

    productos = {}
    for nombre, precio, estacion in (
        ("Arroz con pollo", "8.50", "kitchen"),
        ("Cerveza", "2.00", "bar"),
    ):
        producto = Product(
            name=nombre, price=Decimal(precio), station=estacion, category_id=categoria.id
        )
        session.add(producto)
        session.commit()
        session.refresh(producto)
        productos[nombre] = producto
    return productos


@pytest.fixture(name="mesa")
def mesa_fixture(session: Session, sede: Branch) -> RestaurantTable:
    zona = Sector(branch_id=sede.id, name="Interior")
    session.add(zona)
    session.commit()
    session.refresh(zona)
    mesa = RestaurantTable(branch_id=sede.id, sector_id=zona.id, number=4)
    session.add(mesa)
    session.commit()
    session.refresh(mesa)
    return mesa


def _tomar(client: TestClient, mesa: RestaurantTable, carta: dict, **extra) -> dict:
    cuerpo = {
        "table_id": str(mesa.id),
        "items": [{"product_id": str(carta["Arroz con pollo"].id), "quantity": 2}],
        **extra,
    }
    respuesta = client.post("/api/orders", json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_tomar_una_comanda_calcula_el_total_y_ocupa_la_mesa(
    client: TestClient, session: Session, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))

    orden = _tomar(client, mesa, carta)

    assert orden["order_number"] == 1
    assert Decimal(str(orden["total"])) == Decimal("17.00")
    assert orden["status"] == "pending"

    session.expire_all()
    assert session.get(RestaurantTable, mesa.id).status == "occupied"


def test_el_precio_se_copia_en_la_linea(
    client: TestClient, session: Session, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """
    Cambiar el precio manana no puede reescribir lo que un cliente ya pago, ni
    renombrar un producto reescribir un recibo impreso.
    """
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    orden = _tomar(client, mesa, carta)

    producto = session.get(Product, carta["Arroz con pollo"].id)
    producto.price = Decimal("99.00")
    producto.name = "Otro nombre"
    session.add(producto)
    session.commit()

    vuelta = client.get(f"/api/orders/{orden['id']}").json()

    assert vuelta["items"][0]["product_name"] == "Arroz con pollo"
    assert Decimal(str(vuelta["items"][0]["unit_price"])) == Decimal("8.50")


def test_los_numeros_empiezan_en_uno_en_cada_sucursal(
    client: TestClient, session: Session, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """
    El numero es el que se canta en voz alta. Que la segunda sede empiece en 40
    porque la primera lleva 39 no le dice nada a nadie.
    """
    norte = crear_sucursal(session, code="NOR", name="Norte")
    zona = Sector(branch_id=norte.id, name="Interior")
    session.add(zona)
    session.commit()
    session.refresh(zona)
    mesa_norte = RestaurantTable(branch_id=norte.id, sector_id=zona.id, number=1)
    session.add(mesa_norte)
    session.commit()
    session.refresh(mesa_norte)

    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    assert _tomar(client, mesa, carta)["order_number"] == 1
    assert _tomar(client, mesa, carta)["order_number"] == 2

    client.cookies.update(cookie_con(MESERO, branch_id=norte.id))
    assert _tomar(client, mesa_norte, carta)["order_number"] == 1


def test_reenviar_la_misma_comanda_NO_duplica(
    client: TestClient, session: Session, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """
    La pieza que hace posible la cola sin conexion sin reescribir el dominio.

    Y no solo «no crea dos filas»: NO vuelve a ocupar la mesa, NO vuelve a
    avisar a cocina y NO gasta otro numero de cuenta. Un `merge()` con clave
    existente haria UPDATE y sobreescribiria con los nulos del objeto entrante.
    """
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    acunado = str(uuid4())

    primera = _tomar(client, mesa, carta, id=acunado)
    segunda = _tomar(client, mesa, carta, id=acunado)

    assert primera["id"] == segunda["id"] == acunado
    assert primera["order_number"] == segunda["order_number"]
    assert len(segunda["items"]) == 1

    session.expire_all()
    assert len(session.exec(select(Order)).all()) == 1


def test_reenviar_una_linea_tampoco_duplica(
    client: TestClient, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    orden = _tomar(client, mesa, carta)
    linea = str(uuid4())
    cuerpo = {"product_id": str(carta["Cerveza"].id), "quantity": 1, "id": linea}

    client.post(f"/api/orders/{orden['id']}/items", json=cuerpo)
    segunda = client.post(f"/api/orders/{orden['id']}/items", json=cuerpo)

    assert len(segunda.json()["items"]) == 2


def test_el_historial_se_escribe_desde_el_primer_estado(
    client: TestClient, session: Session, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """
    Es IMPOSIBLE de reconstruir hacia atras. Si no entra ahora, las metricas de
    tiempo de preparacion solo tendran datos desde el dia que alguien se acuerde.
    """
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    orden = _tomar(client, mesa, carta)
    client.patch(f"/api/orders/{orden['id']}/status", json={"status": "preparing"})

    historial = session.exec(
        select(OrderStatusHistory)
        .where(OrderStatusHistory.order_id == UUID(orden["id"]))
        .order_by(OrderStatusHistory.changed_at)
    ).all()

    assert [(h.from_status, h.to_status) for h in historial] == [
        (None, "pending"),
        ("pending", "preparing"),
    ]


def test_una_transicion_imposible_dice_que_se_puede_hacer(
    client: TestClient, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    orden = _tomar(client, mesa, carta)

    respuesta = client.patch(f"/api/orders/{orden['id']}/status", json={"status": "delivered"})

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "transicion_invalida"
    assert "solo puede ir a" in respuesta.json()["error"]["message"]


def test_no_se_puede_cerrar_una_cuenta_cambiandole_el_estado(
    client: TestClient, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """
    El agujero de dinero mas facil de abrir.

    Si «cerrada» fuera una transicion mas, la cuenta saldria de «por cobrar» y
    la mesa se liberaria sin que entrara nada, y sin dejar rastro.
    """
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    orden = _tomar(client, mesa, carta)
    for estado in ("preparing", "ready", "delivered"):
        client.patch(f"/api/orders/{orden['id']}/status", json={"status": estado})

    respuesta = client.patch(f"/api/orders/{orden['id']}/status", json={"status": "closed"})

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "cierre_sin_cobro"


def test_marcar_dos_veces_no_falla(
    client: TestClient, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """El tablero se toca con prisa: un doble toque no es un error."""
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    orden = _tomar(client, mesa, carta)
    client.patch(f"/api/orders/{orden['id']}/status", json={"status": "preparing"})

    repetido = client.patch(f"/api/orders/{orden['id']}/status", json={"status": "preparing"})

    assert repetido.status_code == 200


def test_el_origen_mostrador_no_se_puede_pedir(
    client: TestClient, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """
    Media funcion de seguridad.

    Si se pudiera pedir, cualquiera con permiso de comandas podria marcar una
    normal como venta de mostrador y hacerla desaparecer del tablero de cocina
    SIN COBRARLA.
    """
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))

    respuesta = client.post(
        "/api/orders",
        json={"table_id": str(mesa.id), "source": "counter", "items": []},
    )

    assert respuesta.status_code == 422


def test_el_tablero_de_cocina_ordena_por_la_hora_del_HECHO(
    client: TestClient, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """
    Una comanda escrita hace diez minutos y enviada ahora va a su sitio de la
    cola, no al final. Es lo que hace que el tablero siga siendo justo cuando
    una tableta se queda sin red un rato.
    """
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    reciente = _tomar(client, mesa, carta)
    vieja = _tomar(client, mesa, carta, occurred_at="2026-09-12T05:00:00Z")

    client.cookies.update(cookie_con(COCINA, branch_id=sede.id))
    tablero = client.get("/api/orders/kds").json()

    assert [o["id"] for o in tablero] == [vieja["id"], reciente["id"]]


def test_el_tablero_filtra_por_estacion(
    client: TestClient, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """Una comanda que solo tiene bebidas no pinta nada en el tablero de cocina."""
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    client.post(
        "/api/orders",
        json={
            "table_id": str(mesa.id),
            "items": [{"product_id": str(carta["Cerveza"].id), "quantity": 1}],
        },
    )

    client.cookies.update(cookie_con(COCINA, branch_id=sede.id))

    assert client.get("/api/orders/kds?estacion=bar").json() != []
    assert client.get("/api/orders/kds?estacion=kitchen").json() == []


def test_cocina_no_puede_editar_la_comanda(
    client: TestClient, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """
    `orders:bump` no es `orders:write`.

    Darle el permiso ancho a la cocina para que pueda tocar un boton es como se
    acaba con un tablero que puede modificar la cuenta.
    """
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    orden = _tomar(client, mesa, carta)

    client.cookies.update(cookie_con(COCINA, branch_id=sede.id))

    assert (
        client.patch(f"/api/orders/{orden['id']}/bump", json={"status": "ready"}).status_code == 200
    )
    assert (
        client.patch(f"/api/orders/{orden['id']}/status", json={"status": "delivered"}).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/orders/{orden['id']}/items", json={"product_id": str(carta["Cerveza"].id)}
        ).status_code
        == 403
    )


def test_cocina_no_puede_anular_desde_el_tablero(
    client: TestClient, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    """Anular una comanda es una decision del salon, no de la cocina."""
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    orden = _tomar(client, mesa, carta)

    client.cookies.update(cookie_con(COCINA, branch_id=sede.id))
    respuesta = client.patch(f"/api/orders/{orden['id']}/bump", json={"status": "cancelled"})

    assert respuesta.status_code == 403


def test_una_sede_no_ve_las_comandas_de_la_otra(
    client: TestClient, session: Session, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    norte = crear_sucursal(session, code="NOR", name="Norte")
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    orden = _tomar(client, mesa, carta)

    client.cookies.update(cookie_con(MESERO, branch_id=norte.id))

    assert client.get("/api/orders").json()["items"] == []
    assert client.get(f"/api/orders/{orden['id']}").status_code == 404


def test_anular_libera_la_mesa_si_no_queda_otra_cuenta(
    client: TestClient, session: Session, sede: Branch, mesa: RestaurantTable, carta: dict
) -> None:
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))
    primera = _tomar(client, mesa, carta)
    segunda = _tomar(client, mesa, carta)

    client.patch(f"/api/orders/{primera['id']}/status", json={"status": "cancelled"})
    session.expire_all()
    # Queda la segunda viva: la mesa NO se libera.
    assert session.get(RestaurantTable, mesa.id).status == "occupied"

    client.patch(f"/api/orders/{segunda['id']}/status", json={"status": "cancelled"})
    session.expire_all()
    assert session.get(RestaurantTable, mesa.id).status == "available"
