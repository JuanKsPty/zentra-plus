"""
Deduplicar lineas de log repetidas.

Un socket rechazado se reconecta cada pocos segundos PARA SIEMPRE: una tableta
olvidada en la barra con el token caducado escribe decenas de miles de lineas
identicas por noche, y con ellas tapa cualquier cosa que si importe.
"""

import time

VENTANA_SEGUNDOS = 60.0

# Tope de claves. NO es decoracion: la clave lleva datos que vienen de fuera —la
# direccion del cliente— asi que sin tope es un agotamiento de memoria de una
# linea.
MAXIMO_CLAVES = 500

_visto: dict[str, float] = {}


def deberia_registrar(clave: str, *, ahora: float | None = None) -> bool:
    momento = ahora if ahora is not None else time.monotonic()

    ultimo = _visto.get(clave)
    if ultimo is not None and momento - ultimo < VENTANA_SEGUNDOS:
        return False

    if len(_visto) >= MAXIMO_CLAVES:
        # Se tira la mitad mas vieja. Es tosco y es suficiente: esto protege la
        # memoria, no ordena nada.
        for vieja in sorted(_visto, key=lambda k: _visto[k])[: MAXIMO_CLAVES // 2]:
            _visto.pop(vieja, None)

    _visto[clave] = momento
    return True


def vaciar() -> None:
    """Solo para las pruebas: el estado global entre casos es una trampa."""
    _visto.clear()
