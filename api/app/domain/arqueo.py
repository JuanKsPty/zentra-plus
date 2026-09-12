"""
La aritmetica del arqueo de caja, aparte del servicio.

Lo que decide si la caja cuadra se prueba con numeros, no levantando una base.
Y el redondeo tiene que ser explicito en un sitio donde una diferencia de un
centavo la acaba pagando el cajero de su bolsillo.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Protocol

from app.domain.order_totals import cuantizar

# Como entra el dinero. `cash` es el unico que cambia lo que hay en el cajon;
# los demas se cotejan contra el datafono o el extracto.
METODOS: Final[tuple[str, ...]] = ("cash", "card", "transfer", "wallet")

ETIQUETAS_DE_METODO: Final[dict[str, str]] = {
    "cash": "Efectivo",
    "card": "Tarjeta",
    "transfer": "Transferencia",
    "wallet": "Billetera",
}


class Cobro(Protocol):
    method: str
    amount: Decimal


@dataclass(frozen=True)
class Arqueo:
    por_metodo: dict[str, Decimal]
    total_vendido: Decimal
    efectivo_vendido: Decimal
    # Lo que deberia haber en el cajon: fondo de apertura + ventas en efectivo.
    efectivo_esperado: Decimal
    efectivo_contado: Decimal | None
    # Contado menos esperado. Negativo es faltante. `None` hasta que se cuenta.
    diferencia: Decimal | None
    cuantos_cobros: int


def arquear(
    cobros: list[Cobro],
    fondo_de_apertura: Decimal,
    efectivo_contado: Decimal | None = None,
) -> Arqueo:
    """
    El desglose de un turno.

    TODOS los metodos aparecen aunque valgan cero: un desglose con huecos obliga
    al cajero a recordar cuales faltan, y es el momento del dia en que menos
    ganas tiene de recordar nada.
    """
    por_metodo = {metodo: Decimal("0.00") for metodo in METODOS}

    for cobro in cobros:
        if cobro.method not in por_metodo:
            continue
        # Se redondea en CADA suma y no solo al final. Con Decimal el error de
        # coma flotante no existe, pero el cajero compara este desglose a mano
        # con el datafono: si el total lleva mas decimales que las partes, la
        # resta no le da y no hay forma de explicarselo.
        por_metodo[cobro.method] = cuantizar(por_metodo[cobro.method] + cobro.amount)

    total = cuantizar(sum(por_metodo.values(), Decimal("0.00")))
    efectivo = por_metodo["cash"]
    esperado = cuantizar(fondo_de_apertura + efectivo)

    return Arqueo(
        por_metodo=por_metodo,
        total_vendido=total,
        efectivo_vendido=efectivo,
        efectivo_esperado=esperado,
        efectivo_contado=efectivo_contado,
        diferencia=None if efectivo_contado is None else cuantizar(efectivo_contado - esperado),
        cuantos_cobros=len(cobros),
    )


def cambio(total: Decimal, recibido: Decimal) -> Decimal:
    """Lo que se devuelve. Nunca negativo: eso seria un pago incompleto."""
    return cuantizar(max(Decimal("0.00"), recibido - total))
