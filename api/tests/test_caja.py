from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import permissions as P
from app.models import (
    Branch,
    Category,
    Order,
    OrderStatusHistory,
    Payment,
    Product,
    RestaurantTable,
    Sector,
)
from tests.factories import cookie_con, crear_sucursal, crear_usuario

CAJERO = [P.CASH_READ, P.CASH_WRITE, P.ORDERS_READ, P.ORDERS_WRITE, P.CATALOG_READ, P.FLOOR_READ]


@pytest.fixture(name="sede")
def sede_fixture(session: Session) -> Branch:
    return crear_sucursal(session)


@pytest.fixture(name="mesa")
def mesa_fixture(session: Session, sede: Branch) -> RestaurantTable:
    zona = Sector(branch_id=sede.id, name="Interior")
    session.add(zona)
    session.commit()
    session.refresh(zona)
    mesa = RestaurantTable(branch_id=sede.id, sector_id=zona.id, number=1)
    session.add(mesa)
    session.commit()
    session.refresh(mesa)
    return mesa


@pytest.fixture(name="producto")
def producto_fixture(session: Session) -> Product:
    categoria = Category(name="Carta")
    session.add(categoria)
    session.commit()
    session.refresh(categoria)
    producto = Product(name="Plato", price=Decimal("10.00"), category_id=categoria.id)
    session.add(producto)
    session.commit()
    session.refresh(producto)
    return producto


@pytest.fixture(name="cajero")
def cajero_fixture(session: Session, sede: Branch) -> UUID:
    usuario = crear_usuario(session, email="caja@zentra.local", sucursales=[sede])
    return usuario.id


def _sesion(client: TestClient, sede: Branch, cajero: UUID) -> None:
    client.cookies.update(cookie_con(CAJERO, branch_id=sede.id, user_id=cajero))


def _cuenta(client: TestClient, mesa: RestaurantTable, producto: Product) -> dict:
    return client.post(
        "/api/orders",
        json={
            "table_id": str(mesa.id),
            "items": [{"product_id": str(producto.id), "quantity": 2}],
        },
    ).json()


# --- turnos -----------------------------------------------------------------


def test_sin_caja_abierta_la_respuesta_es_nula_no_un_error(
    client: TestClient, sede: Branch, cajero: UUID
) -> None:
    """«No tienes caja abierta» es el primer estado del dia, no un fallo."""
    _sesion(client, sede, cajero)

    respuesta = client.get("/api/shifts/current")

    assert respuesta.status_code == 200
    assert respuesta.json() is None


def test_abrir_dos_veces_da_un_error_de_negocio_no_un_500(
    client: TestClient, sede: Branch, cajero: UUID
) -> None:
    """
    El doble clic.

    Sin el indice parcial, esto abriria DOS turnos: los cobros se repartirian
    entre los dos y no cuadraria ninguno — peor que no cuadrar uno, porque nadie
    sabe cual mirar.
    """
    _sesion(client, sede, cajero)
    assert client.post("/api/shifts/open", json={"opening_cash": "50.00"}).status_code == 201

    repetido = client.post("/api/shifts/open", json={"opening_cash": "50.00"})

    assert repetido.status_code == 409
    assert repetido.json()["error"]["code"] == "turno_ya_abierto"


def test_dos_cajeros_pueden_tener_caja_abierta_a_la_vez(
    client: TestClient, session: Session, sede: Branch, cajero: UUID
) -> None:
    otro = crear_usuario(session, email="otro@zentra.local", sucursales=[sede]).id

    _sesion(client, sede, cajero)
    assert client.post("/api/shifts/open", json={"opening_cash": "50.00"}).status_code == 201

    client.cookies.update(cookie_con(CAJERO, branch_id=sede.id, user_id=otro))
    assert client.post("/api/shifts/open", json={"opening_cash": "30.00"}).status_code == 201


def test_el_mismo_cajero_puede_abrir_caja_en_dos_sucursales(
    client: TestClient, session: Session, sede: Branch, cajero: UUID
) -> None:
    """
    El indice es por cajero Y SUCURSAL. En LoklFlow era solo por cajero, lo que
    impedia que un gerente cubriera dos sedes.
    """
    norte = crear_sucursal(session, code="NOR", name="Norte")

    _sesion(client, sede, cajero)
    assert client.post("/api/shifts/open", json={"opening_cash": "50.00"}).status_code == 201

    client.cookies.update(cookie_con(CAJERO, branch_id=norte.id, user_id=cajero))
    assert client.post("/api/shifts/open", json={"opening_cash": "20.00"}).status_code == 201


# --- cobro ------------------------------------------------------------------


def test_no_se_puede_cobrar_sin_caja_abierta(
    client: TestClient, sede: Branch, cajero: UUID, mesa: RestaurantTable, producto: Product
) -> None:
    """
    Se comprueba ANTES de escribir nada. Un cobro sin turno no tendria a que
    arqueo pertenecer, y apareceria un ingreso que ninguna caja explica.
    """
    _sesion(client, sede, cajero)
    cuenta = _cuenta(client, mesa, producto)

    respuesta = client.post(
        f"/api/orders/{cuenta['id']}/payments", json={"method": "cash", "amount": "20.00"}
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "sin_turno"


def test_cobrar_a_medias_cierra_la_cuenta_al_saldarla(
    client: TestClient,
    session: Session,
    sede: Branch,
    cajero: UUID,
    mesa: RestaurantTable,
    producto: Product,
) -> None:
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "50.00"})
    cuenta = _cuenta(client, mesa, producto)

    primero = client.post(
        f"/api/orders/{cuenta['id']}/payments", json={"method": "cash", "amount": "8.00"}
    ).json()
    assert Decimal(str(primero["due"])) == Decimal("12.00")
    assert primero["is_settled"] is False

    segundo = client.post(
        f"/api/orders/{cuenta['id']}/payments", json={"method": "card", "amount": "12.00"}
    ).json()
    assert Decimal(str(segundo["due"])) == Decimal("0.00")
    assert segundo["is_settled"] is True

    session.expire_all()
    assert session.get(Order, UUID(cuenta["id"])).status == "closed"


def test_al_cobrar_la_mesa_queda_POR_RECOGER_no_libre(
    client: TestClient,
    session: Session,
    sede: Branch,
    cajero: UUID,
    mesa: RestaurantTable,
    producto: Product,
) -> None:
    """
    Una mesa recien cobrada no esta lista: hay que recogerla. Si el sistema
    dijera «libre», el anfitrion sienta a alguien encima de los platos del
    anterior.
    """
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "50.00"})
    cuenta = _cuenta(client, mesa, producto)
    client.post(f"/api/orders/{cuenta['id']}/payments", json={"method": "cash", "amount": "20.00"})

    session.expire_all()
    assert session.get(RestaurantTable, mesa.id).status == "cleaning"


def test_un_pago_parcial_reenviado_NO_cobra_dos_veces(
    client: TestClient,
    session: Session,
    sede: Branch,
    cajero: UUID,
    mesa: RestaurantTable,
    producto: Product,
) -> None:
    """
    EL caso que justifica la clave de reenvio.

    Un pago COMPLETO repetido se rechazaria de rebote, porque la cuenta ya esta
    cerrada. Pero uno parcial pasa entero: 8 + 8 sobre una cuenta de 20 se cobra
    dos veces y el arqueo sale con ocho de mas.
    """
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "50.00"})
    cuenta = _cuenta(client, mesa, producto)
    cuerpo = {"method": "cash", "amount": "8.00", "client_request_id": str(uuid4())}

    client.post(f"/api/orders/{cuenta['id']}/payments", json=cuerpo)
    segundo = client.post(f"/api/orders/{cuenta['id']}/payments", json=cuerpo).json()

    assert Decimal(str(segundo["paid"])) == Decimal("8.00")
    assert len(segundo["payments"]) == 1
    session.expire_all()
    assert len(session.exec(select(Payment)).all()) == 1


def test_el_reenvio_se_mira_ANTES_que_el_estado_de_la_cuenta(
    client: TestClient, sede: Branch, cajero: UUID, mesa: RestaurantTable, producto: Product
) -> None:
    """
    El orden de las comprobaciones, y no es cosmetico.

    El cobro original CERRO la cuenta. Si el reintento comprobara primero el
    estado, chocaria contra «esa cuenta ya esta pagada» — un fallo FALSO que
    dejaria la cola reintentando algo que ya se aplico.
    """
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "50.00"})
    cuenta = _cuenta(client, mesa, producto)
    cuerpo = {"method": "cash", "amount": "20.00", "client_request_id": str(uuid4())}

    client.post(f"/api/orders/{cuenta['id']}/payments", json=cuerpo)
    reintento = client.post(f"/api/orders/{cuenta['id']}/payments", json=cuerpo)

    assert reintento.status_code == 201
    assert reintento.json()["is_settled"] is True


def test_una_cuenta_ya_pagada_no_admite_otro_cobro(
    client: TestClient, sede: Branch, cajero: UUID, mesa: RestaurantTable, producto: Product
) -> None:
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "50.00"})
    cuenta = _cuenta(client, mesa, producto)
    client.post(f"/api/orders/{cuenta['id']}/payments", json={"method": "cash", "amount": "20.00"})

    otro = client.post(
        f"/api/orders/{cuenta['id']}/payments", json={"method": "cash", "amount": "5.00"}
    )

    assert otro.status_code == 409
    assert otro.json()["error"]["code"] == "cuenta_saldada"


def test_una_cuenta_anulada_no_se_cobra(
    client: TestClient, sede: Branch, cajero: UUID, mesa: RestaurantTable, producto: Product
) -> None:
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "50.00"})
    cuenta = _cuenta(client, mesa, producto)
    client.patch(f"/api/orders/{cuenta['id']}/status", json={"status": "cancelled"})

    respuesta = client.post(
        f"/api/orders/{cuenta['id']}/payments", json={"method": "cash", "amount": "20.00"}
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "comanda_anulada"


def test_el_cierre_por_cobro_deja_rastro_en_el_historial(
    client: TestClient,
    session: Session,
    sede: Branch,
    cajero: UUID,
    mesa: RestaurantTable,
    producto: Product,
) -> None:
    """
    El cierre se salta la maquina de estados —que rechaza `closed` siempre— pero
    NO se salta el historial: sin la fila, el reporte de tiempos veria una
    cuenta que nunca se cerro.
    """
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "50.00"})
    cuenta = _cuenta(client, mesa, producto)
    client.post(f"/api/orders/{cuenta['id']}/payments", json={"method": "cash", "amount": "20.00"})

    historial = session.exec(
        select(OrderStatusHistory).where(OrderStatusHistory.order_id == UUID(cuenta["id"]))
    ).all()

    assert [h.to_status for h in historial][-1] == "closed"


def test_un_metodo_inventado_se_rechaza(
    client: TestClient, sede: Branch, cajero: UUID, mesa: RestaurantTable, producto: Product
) -> None:
    _sesion(client, sede, cajero)
    client.post("/api/shifts/open", json={"opening_cash": "50.00"})
    cuenta = _cuenta(client, mesa, producto)

    respuesta = client.post(
        f"/api/orders/{cuenta['id']}/payments", json={"method": "trueque", "amount": "20.00"}
    )

    assert respuesta.status_code == 422


# --- arqueo -----------------------------------------------------------------


def test_el_arqueo_cuadra_de_punta_a_punta(
    client: TestClient, sede: Branch, cajero: UUID, mesa: RestaurantTable, producto: Product
) -> None:
    _sesion(client, sede, cajero)
    turno = client.post("/api/shifts/open", json={"opening_cash": "50.00"}).json()
    cuenta = _cuenta(client, mesa, producto)
    client.post(f"/api/orders/{cuenta['id']}/payments", json={"method": "cash", "amount": "12.00"})
    client.post(f"/api/orders/{cuenta['id']}/payments", json={"method": "card", "amount": "8.00"})

    cierre = client.post(f"/api/shifts/{turno['id']}/close", json={"closing_cash": "62.00"}).json()

    assert Decimal(str(cierre["cash_sold"])) == Decimal("12.00")
    assert Decimal(str(cierre["expected_cash"])) == Decimal("62.00")
    assert Decimal(str(cierre["difference"])) == Decimal("0.00")
    assert Decimal(str(cierre["total_sold"])) == Decimal("20.00")
    assert cierre["shift"]["status"] == "closed"


def test_no_se_cierra_la_caja_con_cuentas_vivas(
    client: TestClient, sede: Branch, cajero: UUID, mesa: RestaurantTable, producto: Product
) -> None:
    """
    Cerrar con cuentas vivas dejaria cobros de este turno cayendo en el
    siguiente, y entonces no cuadraria ninguno de los dos.
    """
    _sesion(client, sede, cajero)
    turno = client.post("/api/shifts/open", json={"opening_cash": "50.00"}).json()
    cuenta = _cuenta(client, mesa, producto)
    client.post(f"/api/orders/{cuenta['id']}/payments", json={"method": "cash", "amount": "5.00"})

    respuesta = client.post(f"/api/shifts/{turno['id']}/close", json={"closing_cash": "55.00"})

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "cuentas_abiertas"
    # Y dice CUALES, con su numero: buscarlas a ciegas al cerrar es lo que hace
    # que el cajero se vaya sin cerrar.
    assert f"#{cuenta['order_number']}" in respuesta.json()["error"]["message"]


def test_no_se_cierra_la_caja_de_otro(
    client: TestClient, session: Session, sede: Branch, cajero: UUID
) -> None:
    """Cerrar la caja de otro deja su arqueo a nombre de quien no la conto."""
    _sesion(client, sede, cajero)
    turno = client.post("/api/shifts/open", json={"opening_cash": "50.00"}).json()

    otro = crear_usuario(session, email="otro@zentra.local", sucursales=[sede]).id
    client.cookies.update(cookie_con(CAJERO, branch_id=sede.id, user_id=otro))

    respuesta = client.post(f"/api/shifts/{turno['id']}/close", json={"closing_cash": "50.00"})

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "caja_ajena"


def test_el_arqueo_de_otra_sucursal_no_se_ve(
    client: TestClient, session: Session, sede: Branch, cajero: UUID
) -> None:
    _sesion(client, sede, cajero)
    turno = client.post("/api/shifts/open", json={"opening_cash": "50.00"}).json()

    norte = crear_sucursal(session, code="NOR", name="Norte")
    client.cookies.update(cookie_con(CAJERO, branch_id=norte.id, user_id=cajero))

    assert client.get(f"/api/shifts/{turno['id']}/summary").status_code == 404


def test_leer_no_basta_para_cobrar(
    client: TestClient, sede: Branch, cajero: UUID, mesa: RestaurantTable, producto: Product
) -> None:
    _sesion(client, sede, cajero)
    cuenta = _cuenta(client, mesa, producto)

    client.cookies.update(
        cookie_con([P.CASH_READ, P.ORDERS_READ], branch_id=sede.id, user_id=cajero)
    )

    assert client.post("/api/shifts/open", json={"opening_cash": "1"}).status_code == 403
    assert (
        client.post(
            f"/api/orders/{cuenta['id']}/payments", json={"method": "cash", "amount": "1"}
        ).status_code
        == 403
    )
