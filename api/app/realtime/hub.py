"""
Quien esta escuchando y a que.

Cada conexion tiene su propia cola. El emisor deja el aviso en las colas que
tocan y se va: no espera a que nadie lo lea, porque un cliente lento no puede
retrasar el cobro que genero el aviso.

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

from app.realtime.events import CANAL_DE, Canal

logger = logging.getLogger("zentra.realtime")

# Cuantos avisos se acumulan antes de empezar a tirar los viejos. Un cliente que
# no lee no puede hacer crecer la memoria sin limite; y como el evento es una
# senal —«mira otra vez»— perder los intermedios no pierde informacion: con leer
# el ultimo, el cliente se pone al dia igual.
COLA_MAXIMA = 100


class Suscripcion:
    def __init__(self, branch_id: UUID, canales: list[Canal]) -> None:
        self.branch_id = branch_id
        self.canales = canales
        self.cola: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=COLA_MAXIMA)

    def encolar(self, evento: dict[str, Any]) -> None:
        try:
            self.cola.put_nowait(evento)
        except asyncio.QueueFull:
            # Se tira el mas viejo y entra el nuevo: al cliente le sirve mas
            # enterarse de lo ultimo que de lo primero.
            with contextlib.suppress(asyncio.QueueEmpty):
                self.cola.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                self.cola.put_nowait(evento)


class Hub:
    def __init__(self) -> None:
        self._suscripciones: dict[tuple[UUID, Canal], set[Suscripcion]] = defaultdict(set)
        # El bucle de eventos del proceso, capturado al arrancar. Hace falta
        # porque los servicios son SINCRONOS y corren en el threadpool: desde
        # ahi no se puede tocar una cola de asyncio sin pasar por el bucle.
        self._bucle: asyncio.AbstractEventLoop | None = None

    def registrar_bucle(self, bucle: asyncio.AbstractEventLoop) -> None:
        self._bucle = bucle

    def suscribir(self, branch_id: UUID, canales: list[Canal]) -> Suscripcion:
        suscripcion = Suscripcion(branch_id, canales)
        for canal in canales:
            self._suscripciones[(branch_id, canal)].add(suscripcion)
        return suscripcion

    def desuscribir(self, suscripcion: Suscripcion) -> None:
        for canal in suscripcion.canales:
            self._suscripciones[(suscripcion.branch_id, canal)].discard(suscripcion)

    def escuchando(self, branch_id: UUID, canal: Canal) -> int:
        return len(self._suscripciones[(branch_id, canal)])

    def publicar(self, evento: dict[str, Any]) -> None:
        canal = CANAL_DE[evento["tipo"]]
        branch_id = UUID(evento["branchId"])
        for suscripcion in list(self._suscripciones[(branch_id, canal)]):
            suscripcion.encolar(evento)

    def publicar_desde_hilo(self, evento: dict[str, Any]) -> None:
        """
        Publica desde codigo sincrono, que es todo el dominio.

        Los servicios corren en el threadpool de anyio, y las colas de asyncio
        no son seguras entre hilos: hay que dejar el trabajo en el bucle. No se
        espera el resultado — que un cliente no reciba un aviso no puede hacer
        fallar el cobro que lo genero.

        Sin bucle registrado (en las pruebas, en un script) no revienta:
        sencillamente no sale.
        """
        if self._bucle is None:
            return
        with contextlib.suppress(RuntimeError):
            self._bucle.call_soon_threadsafe(self.publicar, evento)


hub = Hub()
