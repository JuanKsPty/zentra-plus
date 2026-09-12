import logging
from uuid import UUID

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core import permissions as P
from app.core.security import leer_ticket
from app.realtime import throttle
from app.realtime.events import Canal
from app.realtime.hub import hub

logger = logging.getLogger("zentra.realtime")

router = APIRouter(tags=["tiempo real"])

# Que permiso abre que canal. Un cocinero no tiene por que enterarse de los
# movimientos de caja.
CANAL_POR_PERMISO: dict[Canal, str] = {
    "orders": P.ORDERS_READ,
    "floor": P.FLOOR_READ,
    "cash": P.CASH_READ,
}

# Codigos de cierre. El cliente los distingue para saber si reintentar: con
# 4401 pide un ticket nuevo, con 4403 no insiste.
CIERRE_SIN_TICKET = 4401
CIERRE_SIN_CANALES = 4403


@router.websocket("/ws")
async def canal(websocket: WebSocket, ticket: str = Query(default="")) -> None:
    """
    El canal de avisos. Dice «mira otra vez», no manda datos.

    Asi un evento perdido por una reconexion no pierde nada: el estado sigue en
    la base y el cliente vuelve a pedirlo.
    """
    origen = websocket.client.host if websocket.client else "desconocido"

    try:
        carga = leer_ticket(ticket)
    except jwt.PyJWTError as error:
        # Se acepta la conexion antes de cerrarla con motivo: si se rechaza el
        # handshake a secas, el navegador solo ve «connection failed» y el
        # cliente no puede distinguir «pide otro ticket» de «no insistas».
        await websocket.accept()
        # Deduplicado por origen: una tableta olvidada con el token caducado
        # reconecta cada pocos segundos para siempre.
        if throttle.deberia_registrar(f"ws:{origen}"):
            logger.info("ticket de WebSocket rechazado desde %s: %s", origen, error)
        await websocket.close(code=CIERRE_SIN_TICKET, reason="Ticket invalido o caducado")
        return

    branch_id = UUID(str(carga["branch_id"]))
    permisos = set(carga.get("permissions", []))
    canales: list[Canal] = [
        canal for canal, permiso in CANAL_POR_PERMISO.items() if permiso in permisos
    ]

    if not canales:
        await websocket.accept()
        await websocket.close(code=CIERRE_SIN_CANALES, reason="Sin canales que escuchar")
        return

    await websocket.accept()
    hub.suscribir(websocket, branch_id, canales)
    await websocket.send_json({"tipo": "conectado", "canales": canales})

    try:
        while True:
            # El cliente no manda nada util; esto mantiene viva la conexion y
            # detecta el cierre. Un `ping` explicito lo contestamos porque un
            # socket puede quedarse «abierto» y muerto tras un cambio de WiFi, y
            # el unico modo de notarlo es que deje de contestar.
            mensaje = await websocket.receive_text()
            if mensaje == "ping":
                await websocket.send_json({"tipo": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        hub.desuscribir(websocket, branch_id, canales)
