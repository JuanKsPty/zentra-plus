"""
Los importes de una comanda. Funciones puras, sin base de datos.

Lo que decide si la caja cuadra se prueba con numeros, no levantando una base.
Y el redondeo tiene que ser explicito en un sitio donde una diferencia de un
centavo la acaba pagando el cajero de su bolsillo.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

CENTAVO = Decimal("0.01")

# Media unidad del ultimo digito representable. Se usa para COMPARAR saldos,
# nunca para redondear: `pagado < total` con decimales exactos deberia bastar,
# pero un importe que entro por otra via puede traer mas decimales.
EPSILON = Decimal("0.005")


def cuantizar(valor: Decimal) -> Decimal:
    """
    Dos decimales, redondeando HACIA ARRIBA en el empate.

    `ROUND_HALF_UP` y no el `ROUND_HALF_EVEN` que Python trae por defecto: el
    redondeo bancario convierte 0.125 en 0.12, y eso no se puede explicar en el
    mostrador. La caja registradora de al lado redondea hacia arriba.
    """
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


class ConAjuste(Protocol):
    price_adjustment: Decimal


class LineaValorada(Protocol):
    subtotal: Decimal
    status: str


def subtotal_de_linea(
    cantidad: int, precio_unitario: Decimal, ajustes: list[Decimal] | None = None
) -> Decimal:
    """
    (precio + ajustes de los modificadores) x cantidad.

    Se redondea DESPUES de multiplicar, no antes. Redondear el ajuste unitario y
    luego multiplicar por ocho multiplica el error por ocho.

    Los ajustes pueden ser negativos: «sin queso, -0.50» es tan valido como
    «extra queso».
    """
    suma_ajustes = sum(ajustes or [], Decimal("0.00"))
    return cuantizar((precio_unitario + suma_ajustes) * cantidad)


def totales(
    lineas: list[LineaValorada],
    propina: Decimal = Decimal("0.00"),
) -> tuple[Decimal, Decimal]:
    """
    Devuelve (subtotal, total).

    Las lineas ANULADAS no suman, pero siguen en la comanda: borrarlas dejaria
    sin rastro que alguien pidio algo y se arrepintio, que es informacion que la
    cocina ya uso.

    El total nunca queda negativo. Es una red de seguridad, no la validacion:
    quien aplica un descuento debe rechazarlo antes con un mensaje; este tope
    solo evita que un importe absurdo se convierta en un cobro negativo que
    descuadre la caja.
    """
    activas = [linea for linea in lineas if linea.status != "cancelled"]
    subtotal = cuantizar(sum((linea.subtotal for linea in activas), Decimal("0.00")))
    total = cuantizar(max(Decimal("0.00"), subtotal + propina))
    return subtotal, total


def falta_por_cobrar(total: Decimal, pagado: Decimal) -> Decimal:
    """Lo que queda. Nunca negativo: un pago de mas es cambio, no saldo."""
    return cuantizar(max(Decimal("0.00"), total - pagado))


def esta_saldada(total: Decimal, pagado: Decimal) -> bool:
    return pagado >= total - EPSILON
