"""
La maquina de estados de una comanda.

Un unico diccionario del que salen la validacion, la documentacion y las
pruebas. Con `if` repartidos por el servicio, cada pantalla nueva anade el suyo
y al tercer mes nadie sabe que transiciones existen.
"""

from typing import Final

ESTADOS: Final = ("pending", "preparing", "ready", "delivered", "closed", "cancelled")

# Como se lee cada estado en pantalla. Va aqui y no en el frontend porque es
# vocabulario del dominio: si la API lo llama «ready», la cocina tiene que ver
# siempre la misma palabra, la escriba quien la escriba.
ETIQUETAS: Final[dict[str, str]] = {
    "pending": "Pendiente",
    "preparing": "En preparacion",
    "ready": "Lista",
    "delivered": "Entregada",
    "closed": "Cobrada",
    "cancelled": "Anulada",
}

TRANSICIONES: Final[dict[str, tuple[str, ...]]] = {
    "pending": ("preparing", "ready", "cancelled"),
    # «ready» directo desde «pending» existe para la barra: un refresco no pasa
    # por «en preparacion», y obligar a dos toques para servir un agua es como
    # se consigue que la gente deje de usar el tablero.
    "preparing": ("ready", "cancelled"),
    "ready": ("delivered", "cancelled"),
    "delivered": ("closed", "cancelled"),
    # Terminales. Una comanda cobrada no vuelve atras: si hubo un error, se
    # anula con su propio movimiento y queda el rastro de los dos.
    "closed": (),
    "cancelled": (),
}

# Las que siguen vivas en el salon. Es el filtro de casi toda pantalla
# operativa, y por eso se deriva de TRANSICIONES en vez de escribirse aparte:
# una lista repetida es una lista que se queda vieja.
ABIERTAS: Final[tuple[str, ...]] = tuple(
    estado for estado, siguientes in TRANSICIONES.items() if siguientes
)

# Las que la cocina todavia tiene que atender.
EN_COCINA: Final[tuple[str, ...]] = ("pending", "preparing")


def es_terminal(estado: str) -> bool:
    return not TRANSICIONES.get(estado, ())


def puede_pasar(desde: str, hasta: str) -> bool:
    return hasta in TRANSICIONES.get(desde, ())


def motivo_si_no_puede(desde: str, hasta: str) -> str | None:
    """
    Por que no se puede, en palabras que sirvan a quien lo lee.

    Un «transicion invalida» obliga al operario a adivinar; «una comanda cobrada
    ya no se puede modificar» le dice que hacer.
    """
    if hasta not in ESTADOS:
        return f"«{hasta}» no es un estado de comanda."
    if desde == hasta:
        return None
    if es_terminal(desde):
        return f"Una comanda {ETIQUETAS[desde].lower()} ya no se puede cambiar."
    if not puede_pasar(desde, hasta):
        posibles = ", ".join(ETIQUETAS[e].lower() for e in TRANSICIONES[desde])
        return (
            f"Una comanda {ETIQUETAS[desde].lower()} no puede pasar a "
            f"{ETIQUETAS[hasta].lower()}. Desde ahi solo puede ir a: {posibles}."
        )
    return None
