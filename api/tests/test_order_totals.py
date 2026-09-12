from dataclasses import dataclass
from decimal import Decimal

import pytest

from app.domain.order_totals import (
    cuantizar,
    esta_saldada,
    falta_por_cobrar,
    subtotal_de_linea,
    totales,
)


@dataclass
class Linea:
    subtotal: Decimal
    status: str = "pending"


def test_el_subtotal_de_una_linea_multiplica_despues_de_sumar_ajustes() -> None:
    # (8.50 + 1.00) x 2
    assert subtotal_de_linea(2, Decimal("8.50"), [Decimal("1.00")]) == Decimal("19.00")


def test_un_ajuste_puede_ser_negativo() -> None:
    """«Sin queso, -0.50» es tan valido como «extra queso»."""
    assert subtotal_de_linea(1, Decimal("8.50"), [Decimal("-0.50")]) == Decimal("8.00")


def test_se_redondea_DESPUES_de_multiplicar() -> None:
    """
    Redondear el ajuste unitario y luego multiplicar por ocho multiplica el
    error por ocho. Con 0.333 x 3: si se redondea antes, 0.33 x 3 = 0.99.
    """
    assert subtotal_de_linea(3, Decimal("0.333")) == Decimal("1.00")


def test_el_empate_redondea_hacia_arriba() -> None:
    """
    `ROUND_HALF_UP`, no el bancario que Python trae por defecto.

    El bancario convierte 0.125 en 0.12, y eso no se puede explicar en el
    mostrador: la caja registradora de al lado redondea hacia arriba.
    """
    assert cuantizar(Decimal("0.125")) == Decimal("0.13")
    assert cuantizar(Decimal("0.135")) == Decimal("0.14")


def test_las_lineas_anuladas_no_suman_pero_siguen_ahi() -> None:
    lineas = [
        Linea(Decimal("10.00")),
        Linea(Decimal("5.00"), status="cancelled"),
        Linea(Decimal("2.50")),
    ]

    subtotal, total = totales(lineas)

    assert subtotal == Decimal("12.50")
    assert total == Decimal("12.50")


def test_la_propina_suma() -> None:
    subtotal, total = totales([Linea(Decimal("20.00"))], propina=Decimal("3.00"))

    assert subtotal == Decimal("20.00")
    assert total == Decimal("23.00")


def test_el_total_nunca_queda_negativo() -> None:
    """
    Red de seguridad, no validacion. Quien aplica un descuento debe rechazarlo
    antes con un mensaje; esto solo evita que un importe absurdo se convierta en
    un cobro negativo que descuadre la caja.
    """
    _, total = totales([Linea(Decimal("5.00"))], propina=Decimal("-100.00"))

    assert total == Decimal("0.00")


def test_una_comanda_sin_lineas_suma_cero() -> None:
    assert totales([]) == (Decimal("0.00"), Decimal("0.00"))


def test_lo_que_falta_nunca_es_negativo() -> None:
    """Un pago de mas es cambio, no saldo a favor."""
    assert falta_por_cobrar(Decimal("10.00"), Decimal("12.00")) == Decimal("0.00")
    assert falta_por_cobrar(Decimal("10.00"), Decimal("4.00")) == Decimal("6.00")


@pytest.mark.parametrize(
    ("total", "pagado", "saldada"),
    [
        (Decimal("10.00"), Decimal("10.00"), True),
        (Decimal("10.00"), Decimal("9.999"), True),  # dentro del epsilon
        (Decimal("10.00"), Decimal("9.99"), False),
        (Decimal("10.00"), Decimal("12.00"), True),
    ],
)
def test_cuando_se_considera_saldada(total: Decimal, pagado: Decimal, saldada: bool) -> None:
    assert esta_saldada(total, pagado) is saldada


def test_sumar_precios_en_decimal_es_exacto() -> None:
    """La razon de que el dinero no sea float, escrita."""
    con_decimal = cuantizar(Decimal("0.10") + Decimal("0.20"))

    assert con_decimal == Decimal("0.30")
    assert 0.1 + 0.2 != 0.3
