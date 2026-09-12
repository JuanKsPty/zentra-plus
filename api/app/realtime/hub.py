"""
Quien esta conectado y a que.

Solo memoria. Con mas de una instancia de la API haria falta un bus —LISTEN /
NOTIFY de PostgreSQL, o Redis— y este modulo es donde se enchufaria: el resto
del codigo habla con `publicar()` y no sabe como llega.
"""

import asyncio
import contextlib
import logging
from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from app.realtime.events import CANAL_DE, Canal

logger = logging.getLogger("zentra.realtime")


class Hub:
    def __init__(self) -> None:
        self._conexiones: dict[tuple[UUID, Canal], set[WebSocket]] = defaultdict(set)
        # El bucle de eventos del proceso, capturado al arrancar. Hace falta
        # porque los servicios son SINCRONOS y corren en el threadpool: desde
        # ahi no se puede hacer `await`, asi que se empuja al bucle.
        self._bucle: asyncio.AbstractEventLoop | None = None

    def registrar_bucle(self, bucle: asyncio.AbstractEventLoop) -> None:
        self._bucle = bucle

    def suscribir(self, socket: WebSocket, branch_id: UUID, canales: list[Canal]) -> None:
        for canal in canales:
            self._conexiones[(branch_id, canal)].add(socket)

    def desuscribir(self, socket: WebSocket, branch_id: UUID, canales: list[Canal]) -> None:
        for canal in canales:
            self._conexiones[(branch_id, canal)].discard(socket)

    def conectados(self, branch_id: UUID, canal: Canal) -> int:
        return len(self._conexiones[(branch_id, canal)])

    async def publicar(self, evento: dict[str, Any]) -> None:
        canal = CANAL_DE[evento["tipo"]]
        branch_id = UUID(evento["branchId"])

        # Copia de la lista: enviar puede fallar y eso modifica el conjunto
        # mientras se recorre.
        for socket in list(self._conexiones[(branch_id, canal)]):
            try:
                await socket.send_json(evento)
            except Exception:
                # Un socket muerto no puede impedir que los demas se enteren.
                # Se descarta y se sigue; el cliente reconectara por su cuenta.
                self._conexiones[(branch_id, canal)].discard(socket)

    def publicar_desde_hilo(self, evento: dict[str, Any]) -> None:
        """
        Publica desde codigo sincrono, que es todo el dominio.

        Los servicios corren en el threadpool de anyio y desde ahi no se puede
        hacer `await`. Esto empuja la corrutina al bucle principal y NO espera
        el resultado: que un cliente no reciba un aviso no puede hacer fallar el
        cobro que lo genero.
        """
        if self._bucle is None:
            return
        with contextlib.suppress(RuntimeError):
            asyncio.run_coroutine_threadsafe(self.publicar(evento), self._bucle)


hub = Hub()
