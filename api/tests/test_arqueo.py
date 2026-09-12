from dataclasses import dataclass
from decimal import Decimal

import pytest

from app.domain.arqueo import METODOS, arquear, cambio


@dataclass
class Pago:
    method: str
    amount: Decimal


def test_todos_los_metodos_aparecen_aunque_valgan_cero() -> None:
    """
    Un desglose con huecos obliga al cajero a recordar cuales faltan, y es el
    momento del dia en que menos ganas tiene de recordar nada.
    """
    resultado = arquear([Pago("cash", Decimal("10.00"))], Decimal("50.00"))

    assert set(resultado.por_metodo) == set(METODOS)
    assert resultado.por_metodo["card"] == Decimal("0.00")


def test_el_efectivo_esperado_es_el_fondo_mas_lo_cobrado_en_efectivo() -> None:
    cobros = [
        Pago("cash", Decimal("20.00")),
        Pago("card", Decimal("35.50")),
        Pago("cash", Decimal("12.25")),
    ]

    resultado = arquear(cobros, Decimal("50.00"))

    assert resultado.efectivo_vendido == Decimal("32.25")
    assert resultado.efectivo_esperado == Decimal("82.25")
    # La tarjeta NO entra en el cajon: se cotejara con el datafono.
    assert resultado.total_vendido == Decimal("67.75")


def test_mientras_el_turno_sigue_abierto_no_hay_diferencia() -> None:
    """`None` y no cero: «no se ha contado» no es lo mismo que «cuadra»."""
    resultado = arquear([Pago("cash", Decimal("10.00"))], Decimal("50.00"))

    assert resultado.efectivo_contado is None
    assert resultado.diferencia is None


def test_un_faltante_sale_negativo() -> None:
    resultado = arquear(
        [Pago("cash", Decimal("40.00"))], Decimal("50.00"), efectivo_contado=Decimal("85.00")
    )

    assert resultado.efectivo_esperado == Decimal("90.00")
    assert resultado.diferencia == Decimal("-5.00")


def test_un_sobrante_sale_positivo() -> None:
    resultado = arquear([], Decimal("50.00"), efectivo_contado=Decimal("52.50"))

    assert resultado.diferencia == Decimal("2.50")


def test_una_caja_que_cuadra_da_exactamente_cero() -> None:
    resultado = arquear(
        [Pago("cash", Decimal("15.35"))], Decimal("20.00"), efectivo_contado=Decimal("35.35")
    )

    assert resultado.diferencia == Decimal("0.00")


def test_el_desglose_cuadra_con_el_total_hasta_el_centimo() -> None:
    """
    Se redondea en CADA suma, no solo al final.

    El cajero compara este desglose a mano con el datafono: si el total llevara
    mas decimales que las partes, la resta no le daria y no habria forma de
    explicarselo.
    """
    cobros = [Pago("card", Decimal("0.005")) for _ in range(200)]

    resultado = arquear(cobros, Decimal("0.00"))

    assert resultado.total_vendido == sum(resultado.por_metodo.values())


def test_un_metodo_desconocido_no_rompe_el_arqueo() -> None:
    """
    Puede llegar de un pago viejo si algun dia se retira un metodo. Que el
    arqueo reviente por eso seria peor que dejarlo fuera del desglose.
    """
    resultado = arquear(
        [Pago("cheque", Decimal("99.00")), Pago("cash", Decimal("1.00"))], Decimal("0.00")
    )

    assert resultado.total_vendido == Decimal("1.00")
    assert resultado.cuantos_cobros == 2


def test_un_turno_sin_ventas_devuelve_el_fondo() -> None:
    resultado = arquear([], Decimal("50.00"), efectivo_contado=Decimal("50.00"))

    assert resultado.efectivo_esperado == Decimal("50.00")
    assert resultado.diferencia == Decimal("0.00")


@pytest.mark.parametrize(
    ("total", "recibido", "esperado"),
    [
        (Decimal("17.00"), Decimal("20.00"), Decimal("3.00")),
        (Decimal("17.00"), Decimal("17.00"), Decimal("0.00")),
        # Pagar de menos no es cambio negativo: es un pago incompleto, y eso lo
        # decide el servicio de cobro, no esta funcion.
        (Decimal("17.00"), Decimal("10.00"), Decimal("0.00")),
    ],
)
def test_el_cambio(total: Decimal, recibido: Decimal, esperado: Decimal) -> None:
    assert cambio(total, recibido) == esperado
