import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core import permissions as P
from app.core.deps import SesionActual, requiere
from app.realtime.events import Canal
from app.realtime.hub import Suscripcion, hub

router = APIRouter(tags=["tiempo real"])

# Que permiso abre que canal. Un cocinero no tiene por que enterarse de los
# movimientos de caja.
CANAL_POR_PERMISO: dict[Canal, str] = {
    "orders": P.ORDERS_READ,
    "floor": P.FLOOR_READ,
    "cash": P.CASH_READ,
}

# Cada cuanto se manda un latido si no hay nada que contar. Sirve para dos
# cosas: mantener viva la conexion a traves de proxies que cortan lo que lleva
# rato callado, y detectar del lado del cliente que la conexion murio.
LATIDO_SEGUNDOS = 20


@router.get(
    "/events",
    dependencies=[Depends(requiere(P.ORDERS_READ))],
    summary="El canal de avisos (SSE)",
)
async def avisos(sesion: SesionActual) -> StreamingResponse:
    """
    Avisos en vivo, por Server-Sent Events.

    POR QUE SSE Y NO UN WEBSOCKET. El navegador habla siempre con su propio
    origen y el servidor de Next reenvia `/api` a la API — y un reenvio de Next
    NO PUEDE atravesar el «upgrade» de un WebSocket. Con Dockerfiles separados y
    sin un proxy de borde delante, el socket no llega. SSE es una respuesta HTTP
    normal que se mantiene abierta, asi que pasa por el mismo camino que todo lo
    demas.

    Y encaja mejor con lo que esto es: el evento es una SENAL —«mira otra vez»—,
    no un canal de datos, asi que no hace falta que el cliente pueda hablar de
    vuelta. De paso se ahorra el pase de un solo uso que un WebSocket habria
    necesitado, porque aqui la cookie de sesion viaja como en cualquier peticion.
    """
    canales: list[Canal] = [
        canal for canal, permiso in CANAL_POR_PERMISO.items() if permiso in sesion.permissions
    ]
    suscripcion = hub.suscribir(sesion.branch_id, canales)

    return StreamingResponse(
        _emitir(suscripcion, canales),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # Sin esto, nginx bufferea la respuesta y los avisos llegan a
            # rafagas de varios minutos, o no llegan.
            "X-Accel-Buffering": "no",
        },
    )


async def _emitir(suscripcion: Suscripcion, canales: list[Canal]) -> AsyncIterator[str]:
    try:
        yield _linea({"tipo": "conectado", "canales": canales})
        while True:
            try:
                evento = await asyncio.wait_for(suscripcion.cola.get(), timeout=LATIDO_SEGUNDOS)
            except TimeoutError:
                # Un comentario de SSE: el cliente lo ignora, los proxies ven
                # trafico y la conexion no se cae por estar callada.
                yield ": latido\n\n"
                continue
            yield _linea(evento)
    finally:
        # Se ejecuta tambien cuando el cliente cierra la pestana: sin esto, cada
        # recarga dejaria una suscripcion huerfana acumulando avisos.
        hub.desuscribir(suscripcion)


def _linea(evento: dict) -> str:
    return f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"
