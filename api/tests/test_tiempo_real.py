import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.routes.events import _emitir
from app.models import Branch
from app.realtime import throttle
from app.realtime.events import sobre
from app.realtime.hub import COLA_MAXIMA, Hub
from tests.factories import crear_sucursal

SEDE_A = UUID("11111111-1111-4111-8111-111111111111")
SEDE_B = UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture(autouse=True)
def _sin_throttle() -> None:
    throttle.vaciar()


@pytest.fixture(name="sede")
def sede_fixture(session: Session) -> Branch:
    return crear_sucursal(session)


def _evento(branch_id: UUID = SEDE_A) -> dict:
    return sobre("order.created", branch_id, orderId="x", orderNumber=1)


# --- el reparto -------------------------------------------------------------


def test_el_aviso_llega_a_quien_escucha_esa_sucursal() -> None:
    hub = Hub()
    aqui = hub.suscribir(SEDE_A, ["orders"])
    alla = hub.suscribir(SEDE_B, ["orders"])

    hub.publicar(_evento(SEDE_A))

    assert aqui.cola.qsize() == 1
    # El tablero del norte no puede llenarse con comandas de la principal.
    assert alla.cola.qsize() == 0


def test_el_aviso_solo_va_a_su_canal() -> None:
    """Un cocinero no tiene por que enterarse de los movimientos de caja."""
    hub = Hub()
    solo_caja = hub.suscribir(SEDE_A, ["cash"])

    hub.publicar(_evento(SEDE_A))

    assert solo_caja.cola.qsize() == 0


def test_quien_escucha_varios_canales_recibe_una_vez_por_evento() -> None:
    hub = Hub()
    todo = hub.suscribir(SEDE_A, ["orders", "floor", "cash"])

    hub.publicar(_evento(SEDE_A))

    assert todo.cola.qsize() == 1


def test_al_desuscribir_deja_de_recibir() -> None:
    """
    Se llama al cerrar la pestana. Sin esto, cada recarga dejaria una
    suscripcion huerfana acumulando avisos que nadie lee.
    """
    hub = Hub()
    suscripcion = hub.suscribir(SEDE_A, ["orders"])

    hub.desuscribir(suscripcion)
    hub.publicar(_evento(SEDE_A))

    assert suscripcion.cola.qsize() == 0
    assert hub.escuchando(SEDE_A, "orders") == 0


def test_un_cliente_que_no_lee_no_hace_crecer_la_memoria() -> None:
    """
    La cola tiene tope y se tiran los MAS VIEJOS.

    Como el evento es una senal —«mira otra vez»— perder los intermedios no
    pierde informacion: leyendo el ultimo, el cliente se pone al dia igual.
    """
    hub = Hub()
    dormido = hub.suscribir(SEDE_A, ["orders"])

    for _ in range(COLA_MAXIMA + 50):
        hub.publicar(_evento(SEDE_A))

    assert dormido.cola.qsize() == COLA_MAXIMA


def test_publicar_sin_bucle_no_revienta() -> None:
    """
    Es lo que pasa en las pruebas y en cualquier script que importe el servicio.
    Que un aviso no salga no puede hacer fallar el cobro que lo genero.
    """
    Hub().publicar_desde_hilo(_evento())


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


# --- el canal ---------------------------------------------------------------


def test_el_canal_necesita_sesion(client: TestClient) -> None:
    assert client.get("/api/events").status_code == 401


def test_el_flujo_empieza_diciendo_a_que_esta_suscrito() -> None:
    """
    Se prueba el generador EN DIRECTO y no a traves del cliente de pruebas.

    Un flujo de SSE no termina nunca por diseno, asi que leerlo desde el cliente
    de pruebas bloquea el hilo y la suite se cuelga — pasa de verdad, y cuesta
    entender porque el sintoma es «pytest no responde». Aqui se pide el primer
    trozo y se cierra.
    """

    async def primer_trozo() -> str:
        flujo = _emitir(Hub().suscribir(SEDE_A, ["orders", "floor"]), ["orders", "floor"])
        try:
            return await anext(flujo)
        finally:
            await flujo.aclose()

    primera = asyncio.run(primer_trozo())

    assert primera.startswith("data: ")
    assert '"tipo": "conectado"' in primera
    assert '"orders"' in primera and '"floor"' in primera
    # Dos saltos de linea cierran un evento de SSE. Sin ellos el navegador se
    # queda esperando y no entrega nada.
    assert primera.endswith("\n\n")


def test_el_flujo_entrega_los_avisos_que_llegan() -> None:
    async def dos_trozos() -> list[str]:
        hub = Hub()
        suscripcion = hub.suscribir(SEDE_A, ["orders"])
        flujo = _emitir(suscripcion, ["orders"])
        await anext(flujo)  # la bienvenida
        hub.publicar(_evento(SEDE_A))
        try:
            return [await anext(flujo)]
        finally:
            await flujo.aclose()

    (aviso,) = asyncio.run(dos_trozos())

    assert '"tipo": "order.created"' in aviso
    assert '"orderNumber": 1' in aviso


def test_al_cerrar_el_flujo_se_suelta_la_suscripcion() -> None:
    """
    Se ejecuta tambien cuando el cliente cierra la pestana. Sin esto, cada
    recarga dejaria una suscripcion huerfana acumulando avisos que nadie lee.
    """

    async def abrir_y_cerrar() -> int:
        from app.realtime.hub import hub as global_hub

        suscripcion = global_hub.suscribir(SEDE_A, ["orders"])
        flujo = _emitir(suscripcion, ["orders"])
        await anext(flujo)
        await flujo.aclose()
        return global_hub.escuchando(SEDE_A, "orders")

    assert asyncio.run(abrir_y_cerrar()) == 0


def test_la_cola_entrega_en_orden() -> None:
    async def comprobar() -> list[int]:
        hub = Hub()
        suscripcion = hub.suscribir(SEDE_A, ["orders"])
        for numero in range(3):
            hub.publicar(sobre("order.created", SEDE_A, orderNumber=numero))
        return [(await suscripcion.cola.get())["payload"]["orderNumber"] for _ in range(3)]

    assert asyncio.run(comprobar()) == [0, 1, 2]


# --- el throttle del log ----------------------------------------------------


def test_los_rechazos_repetidos_solo_se_registran_una_vez() -> None:
    """
    Una tableta olvidada en la barra con la sesion caducada reintenta cada pocos
    segundos PARA SIEMPRE: decenas de miles de lineas identicas por noche que
    tapan cualquier cosa que si importe.
    """
    assert throttle.deberia_registrar("sse:1.2.3.4", ahora=0.0) is True
    assert throttle.deberia_registrar("sse:1.2.3.4", ahora=5.0) is False
    assert throttle.deberia_registrar("sse:1.2.3.4", ahora=61.0) is True
    # Otro origen si se registra: se deduplica la repeticion, no el hecho.
    assert throttle.deberia_registrar("sse:9.9.9.9", ahora=5.0) is True


def test_el_throttle_no_crece_sin_limite() -> None:
    """La clave lleva la direccion del cliente, que viene de fuera."""
    for numero in range(throttle.MAXIMO_CLAVES + 200):
        throttle.deberia_registrar(f"sse:10.0.0.{numero}", ahora=float(numero))

    assert len(throttle._visto) <= throttle.MAXIMO_CLAVES
