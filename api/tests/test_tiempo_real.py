import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import permissions as P
from app.core.security import firmar_acceso, firmar_ticket, leer_ticket
from app.models import Branch
from app.realtime import throttle
from app.realtime.events import sobre
from app.realtime.hub import Hub
from tests.factories import cookie_con, crear_sucursal

MESERO = [P.ORDERS_READ, P.ORDERS_WRITE, P.FLOOR_READ, P.CATALOG_READ]

SEDE_A = UUID("11111111-1111-4111-8111-111111111111")
SEDE_B = UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture(autouse=True)
def _sin_throttle() -> None:
    throttle.vaciar()


@pytest.fixture(name="sede")
def sede_fixture(session: Session) -> Branch:
    return crear_sucursal(session)


# --- el ticket --------------------------------------------------------------


def test_el_ticket_copia_los_permisos_de_la_sesion(client: TestClient, sede: Branch) -> None:
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))

    ticket = client.post("/api/auth/ws-ticket").json()["ticket"]

    carga = leer_ticket(ticket)
    assert carga["branch_id"] == str(sede.id)
    assert set(carga["permissions"]) == set(MESERO)


def test_el_ticket_caduca_enseguida(client: TestClient, sede: Branch) -> None:
    """
    Treinta segundos: lo justo para pedirlo y abrir el socket.

    Va en la URL, asi que puede acabar en un log de acceso o en el historial del
    navegador. Que caduque enseguida es lo que hace que eso no importe.
    """
    client.cookies.update(cookie_con(MESERO, branch_id=sede.id))

    carga = leer_ticket(client.post("/api/auth/ws-ticket").json()["ticket"])

    assert carga["exp"] - carga["iat"] == 30


def test_un_token_de_sesion_NO_vale_como_ticket() -> None:
    """
    Sin esta comprobacion, el token de acceso —que dura horas— serviria para
    abrir sockets, y el ticket no habria servido para nada.
    """
    acceso = firmar_acceso(
        {"sub": str(uuid4()), "name": "T", "branch_id": str(SEDE_A), "permissions": MESERO},
        "email",
    )

    with pytest.raises(jwt.InvalidTokenError):
        leer_ticket(acceso)


def test_pedir_un_ticket_necesita_sesion(client: TestClient) -> None:
    assert client.post("/api/auth/ws-ticket").status_code == 401


# --- el canal ---------------------------------------------------------------


def test_el_canal_suscribe_segun_los_permisos(client: TestClient, sede: Branch) -> None:
    """Un cocinero no tiene por que enterarse de los movimientos de caja."""
    ticket = firmar_ticket(
        {"sub": str(uuid4()), "branch_id": str(sede.id), "permissions": [P.ORDERS_READ]}
    )

    with client.websocket_connect(f"/api/ws?ticket={ticket}") as socket:
        bienvenida = socket.receive_json()

    assert bienvenida["tipo"] == "conectado"
    assert bienvenida["canales"] == ["orders"]


def test_quien_puede_verlo_todo_recibe_los_tres_canales(client: TestClient, sede: Branch) -> None:
    ticket = firmar_ticket(
        {
            "sub": str(uuid4()),
            "branch_id": str(sede.id),
            "permissions": [P.ORDERS_READ, P.FLOOR_READ, P.CASH_READ],
        }
    )

    with client.websocket_connect(f"/api/ws?ticket={ticket}") as socket:
        assert set(socket.receive_json()["canales"]) == {"orders", "floor", "cash"}


def test_el_ping_se_contesta(client: TestClient, sede: Branch) -> None:
    """
    Un socket puede quedarse «abierto» y muerto tras un cambio de WiFi. El unico
    modo de notarlo es que deje de contestar.
    """
    ticket = firmar_ticket(
        {"sub": str(uuid4()), "branch_id": str(sede.id), "permissions": [P.ORDERS_READ]}
    )

    with client.websocket_connect(f"/api/ws?ticket={ticket}") as socket:
        socket.receive_json()
        socket.send_text("ping")
        assert socket.receive_json() == {"tipo": "pong"}


@pytest.mark.parametrize(
    ("ticket", "codigo"),
    [("basura", 4401), ("", 4401)],
)
def test_sin_ticket_valido_se_cierra_con_codigo(
    client: TestClient, ticket: str, codigo: int
) -> None:
    """
    Se acepta la conexion y LUEGO se cierra con motivo.

    Rechazando el handshake a secas, el navegador solo ve «connection failed» y
    el cliente no puede distinguir «pide otro ticket» de «no insistas».
    """
    from starlette.websockets import WebSocketDisconnect

    with (
        pytest.raises(WebSocketDisconnect) as excinfo,
        client.websocket_connect(f"/api/ws?ticket={ticket}") as socket,
    ):
        socket.receive_json()

    assert excinfo.value.code == codigo


def test_sin_ningun_canal_no_se_deja_la_conexion_abierta(client: TestClient, sede: Branch) -> None:
    """Un socket que no puede recibir nada solo gasta una conexion."""
    from starlette.websockets import WebSocketDisconnect

    ticket = firmar_ticket({"sub": str(uuid4()), "branch_id": str(sede.id), "permissions": []})

    with (
        pytest.raises(WebSocketDisconnect) as excinfo,
        client.websocket_connect(f"/api/ws?ticket={ticket}") as socket,
    ):
        socket.receive_json()

    assert excinfo.value.code == 4403


# --- el reparto -------------------------------------------------------------


class SocketFalso:
    """Lo justo para saber que recibio. Montar uno real no anade nada aqui."""

    def __init__(self, *, roto: bool = False) -> None:
        self.recibidos: list[dict] = []
        self.roto = roto

    async def send_json(self, datos: dict) -> None:
        if self.roto:
            raise RuntimeError("socket muerto")
        self.recibidos.append(datos)


def _evento(branch_id: UUID) -> dict:
    return sobre("order.created", branch_id, orderId="x", orderNumber=1)


def test_el_aviso_llega_a_los_suscritos_de_esa_sucursal() -> None:
    hub = Hub()
    aqui, alla = SocketFalso(), SocketFalso()
    hub.suscribir(aqui, SEDE_A, ["orders"])  # type: ignore[arg-type]
    hub.suscribir(alla, SEDE_B, ["orders"])  # type: ignore[arg-type]

    asyncio.run(hub.publicar(_evento(SEDE_A)))

    assert len(aqui.recibidos) == 1
    # El tablero del norte no puede llenarse con comandas de la principal.
    assert alla.recibidos == []


def test_el_aviso_solo_va_a_su_canal() -> None:
    hub = Hub()
    solo_caja = SocketFalso()
    hub.suscribir(solo_caja, SEDE_A, ["cash"])  # type: ignore[arg-type]

    asyncio.run(hub.publicar(_evento(SEDE_A)))

    assert solo_caja.recibidos == []


def test_un_socket_muerto_no_impide_que_los_demas_se_enteren() -> None:
    """Y se descarta: el cliente reconectara por su cuenta."""
    hub = Hub()
    muerto, vivo = SocketFalso(roto=True), SocketFalso()
    hub.suscribir(muerto, SEDE_A, ["orders"])  # type: ignore[arg-type]
    hub.suscribir(vivo, SEDE_A, ["orders"])  # type: ignore[arg-type]

    asyncio.run(hub.publicar(_evento(SEDE_A)))

    assert len(vivo.recibidos) == 1
    assert hub.conectados(SEDE_A, "orders") == 1


def test_publicar_sin_bucle_no_revienta() -> None:
    """
    Es lo que pasa en las pruebas y en cualquier script que importe el servicio.

    Que un aviso no salga no puede hacer fallar el cobro que lo genero.
    """
    Hub().publicar_desde_hilo(_evento(SEDE_A))


def test_el_sobre_lleva_siempre_los_mismos_campos() -> None:
    """
    Se fija en el primer commit del canal. Si luego hubiera que anadir la
    sucursal, habria que tocar cada emisor y cada suscriptor A LA VEZ.
    """
    evento = sobre("order.changed", SEDE_A, orderId="abc")

    assert evento["tipo"] == "order.changed"
    assert evento["branchId"] == str(SEDE_A)
    assert evento["payload"] == {"orderId": "abc"}
    assert datetime.fromisoformat(evento["emitidoEn"]) <= datetime.now(UTC)


# --- el throttle del log ----------------------------------------------------


def test_los_rechazos_repetidos_solo_se_registran_una_vez() -> None:
    """
    Una tableta olvidada en la barra con el token caducado reconecta cada pocos
    segundos PARA SIEMPRE: decenas de miles de lineas identicas por noche que
    tapan cualquier cosa que si importe.
    """
    assert throttle.deberia_registrar("ws:1.2.3.4", ahora=0.0) is True
    assert throttle.deberia_registrar("ws:1.2.3.4", ahora=5.0) is False
    assert throttle.deberia_registrar("ws:1.2.3.4", ahora=61.0) is True
    # Otro origen si se registra: se deduplica la repeticion, no el hecho.
    assert throttle.deberia_registrar("ws:9.9.9.9", ahora=5.0) is True


def test_el_throttle_no_crece_sin_limite() -> None:
    """La clave lleva la direccion del cliente, que viene de fuera."""
    for numero in range(throttle.MAXIMO_CLAVES + 200):
        throttle.deberia_registrar(f"ws:10.0.0.{numero}", ahora=float(numero))

    assert len(throttle._visto) <= throttle.MAXIMO_CLAVES
