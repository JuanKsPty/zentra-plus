from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import permissions as P
from app.models import Branch, Category, Order, Payment, Product
from tests.factories import cookie_con, crear_sucursal, crear_usuario

CAJERO = [P.CASH_READ, P.CASH_WRITE, P.ORDERS_READ, P.ORDERS_WRITE, P.CATALOG_READ]


@pytest.fixture(name="sede")
def sede_fixture(session: Session) -> Branch:
    return crear_sucursal(session)


@pytest.fixture(name="producto")
def producto_fixture(session: Session) -> Product:
    categoria = Category(name="Carta")
    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    producto = Product(
        name="Cafe", price=Decimal("1.50"), station="immediate", category_id=categoria.id
    )
    session.add(producto)
    session.commit()
    session.refresh(producto)
    return producto


@pytest.fixture(name="cajero")
def cajero_fixture(session: Session, sede: Branch) -> UUID:
    return crear_usuario(session, email="caja@zentra.local", sucursales=[sede]).id


def _sesion(client: TestClient, sede: Branch, cajero: UUID) -> None:
    client.cookies.update(cookie_con(CAJERO, branch_id=sede.id, user_id=cajero))


def _venta(producto: Product, **extra) -> dict:
    return {
        "method": "cash",
        "items": [{"product_id": str(producto.id), "quantity": 2}],
        **extra,
    }


def test_vender_crea_cobra_y_cierra_de_una_vez(
    client: TestClient, session: Session, sede: Branch, cajero: UUID, producto: Product
) -> None:
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "20.00"})

    respuesta = client.post("/api/counter-sales", json=_venta(producto))

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert Decimal(str(cuerpo["total"])) == Decimal("3.00")
    assert cuerpo["is_settled"] is True

    session.expire_all()
    venta = session.exec(select(Order)).one()
    assert venta.status == "closed"
    assert venta.source == "counter"
    assert venta.table_id is None


def test_sin_caja_abierta_NO_deja_una_venta_a_medias(
    client: TestClient, session: Session, sede: Branch, cajero: UUID, producto: Product
) -> None:
    """
    El turno se comprueba ANTES de crear nada, aunque el cobro lo mire otra vez.

    Si se dejara solo al cobrar, la comanda ya existiria cuando salta el error y
    quedaria una venta de mostrador abierta —sin mesa, sin nadie mirandola—
    engordando «por cobrar» hasta que alguien la cancele a mano. Y el fallo mas
    probable de este endpoint es el primer uso del dia, justo cuando no hay caja
    abierta.
    """
    _sesion(client, sede, cajero)

    respuesta = client.post("/api/counter-sales", json=_venta(producto))

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "sin_turno"
    # Y NO quedo nada escrito.
    assert session.exec(select(Order)).all() == []


def test_reenviar_la_venta_no_duplica_ni_la_comanda_ni_el_cobro(
    client: TestClient, session: Session, sede: Branch, cajero: UUID, producto: Product
) -> None:
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "20.00"})
    cuerpo = _venta(producto, id=str(uuid4()), client_request_id=str(uuid4()))

    primera = client.post("/api/counter-sales", json=cuerpo).json()
    segunda = client.post("/api/counter-sales", json=cuerpo).json()

    assert primera["order_id"] == segunda["order_id"]
    session.expire_all()
    assert len(session.exec(select(Order)).all()) == 1
    assert len(session.exec(select(Payment)).all()) == 1


def test_la_venta_de_mostrador_entra_en_el_arqueo(
    client: TestClient, sede: Branch, cajero: UUID, producto: Product
) -> None:
    """Una venta de mostrador y una de mesa tienen que sumar igual."""
    _sesion(client, sede, cajero)
    turno = client.post("/api/shifts/open", json={"opening_cash": "20.00"}).json()
    client.post("/api/counter-sales", json=_venta(producto))

    arqueo = client.get(f"/api/shifts/{turno['id']}/summary").json()

    assert Decimal(str(arqueo["cash_sold"])) == Decimal("3.00")
    assert Decimal(str(arqueo["expected_cash"])) == Decimal("23.00")


def test_el_origen_mostrador_sigue_sin_poder_pedirse_en_una_comanda_normal(
    client: TestClient, sede: Branch, cajero: UUID, producto: Product
) -> None:
    """
    Media funcion de seguridad, y esta es la otra mitad: `counter` SOLO lo
    escribe este servicio, que ademas cobra en el mismo acto.
    """
    _sesion(client, sede, cajero)

    respuesta = client.post(
        "/api/orders",
        json={"source": "counter", "items": [{"product_id": str(producto.id)}]},
    )

    assert respuesta.status_code == 422


def test_hacen_falta_LOS_DOS_permisos(
    client: TestClient, sede: Branch, cajero: UUID, producto: Product
) -> None:
    """
    Con uno solo se podria hacer media operacion, que es justo la que no existe.
    """
    for permisos in ([P.ORDERS_WRITE, P.CASH_READ], [P.CASH_WRITE, P.ORDERS_READ]):
        client.cookies.update(cookie_con(permisos, branch_id=sede.id, user_id=cajero))
        assert client.post("/api/counter-sales", json=_venta(producto)).status_code == 403


def test_una_venta_sin_lineas_se_rechaza_ANTES_de_crear_nada(
    client: TestClient, session: Session, sede: Branch, cajero: UUID, producto: Product
) -> None:
    """
    Encontrado escribiendo esta prueba.

    La primera version creaba la comanda y reventaba despues, al construir un
    cobro de cero — dejando exactamente la venta huerfana que este endpoint
    existe para no dejar nunca. Ahora se rechaza en la validacion del cuerpo.
    """
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "20.00"})

    respuesta = client.post("/api/counter-sales", json={"method": "cash", "items": []})

    assert respuesta.status_code == 422
    assert session.exec(select(Order)).all() == []


def test_una_venta_que_suma_cero_tampoco(
    client: TestClient, session: Session, sede: Branch, cajero: UUID
) -> None:
    """El otro camino: lineas que si existen pero no suman nada."""
    from app.models import Category

    categoria = Category(name="Cortesias")
    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    gratis = Product(name="Agua de cortesia", price=Decimal("0.00"), category_id=categoria.id)
    session.add(gratis)
    session.commit()
    session.refresh(gratis)

    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "20.00"})

    respuesta = client.post("/api/counter-sales", json=_venta(gratis))

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "venta_sin_importe"
    assert session.exec(select(Order)).all() == []
