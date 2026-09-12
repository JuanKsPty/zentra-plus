import pytest

from app.domain.order_state import (
    ABIERTAS,
    ESTADOS,
    ETIQUETAS,
    TRANSICIONES,
    es_terminal,
    motivo_si_no_puede,
    puede_pasar,
)


def test_la_matriz_completa_de_transiciones() -> None:
    """
    Cada par posible, comprobado contra la tabla.

    Se recorre el producto cartesiano en vez de escribir los casos a mano: si
    manana se anade un estado, esta prueba lo cubre sola. Escribirlos uno a uno
    es como una tabla acaba con un hueco que nadie ve.
    """
    for desde in ESTADOS:
        for hasta in ESTADOS:
            esperado = hasta in TRANSICIONES[desde]
            assert puede_pasar(desde, hasta) is esperado, f"{desde} -> {hasta}"


def test_cobrada_y_anulada_son_terminales() -> None:
    """
    Una comanda cobrada no vuelve atras. Si hubo un error, se anula con su
    propio movimiento y queda el rastro de los dos.
    """
    assert es_terminal("closed")
    assert es_terminal("cancelled")
    for estado in ("pending", "preparing", "ready", "delivered"):
        assert not es_terminal(estado)


def test_se_puede_anular_desde_cualquier_estado_vivo() -> None:
    for estado in ABIERTAS:
        assert puede_pasar(estado, "cancelled"), estado


def test_un_agua_puede_ir_directa_a_lista() -> None:
    """
    La barra no pasa por «en preparacion».

    Obligar a dos toques para servir un refresco es como se consigue que la
    gente deje de usar el tablero y vuelva a gritar por la ventanilla.
    """
    assert puede_pasar("pending", "ready")


def test_las_abiertas_se_derivan_de_la_tabla() -> None:
    """Una lista repetida es una lista que se queda vieja."""
    assert set(ABIERTAS) == {"pending", "preparing", "ready", "delivered"}


def test_todos_los_estados_tienen_etiqueta() -> None:
    """Si falta una, la pantalla ensena el nombre tecnico en ingles."""
    assert set(ETIQUETAS) == set(ESTADOS)


@pytest.mark.parametrize(
    ("desde", "hasta", "fragmento"),
    [
        ("closed", "preparing", "ya no se puede cambiar"),
        ("pending", "closed", "solo puede ir a"),
        ("pending", "volando", "no es un estado"),
    ],
)
def test_el_motivo_sirve_a_quien_lo_lee(desde: str, hasta: str, fragmento: str) -> None:
    """
    «Transicion invalida» obliga al operario a adivinar. El mensaje tiene que
    decirle que puede hacer desde donde esta.
    """
    motivo = motivo_si_no_puede(desde, hasta)

    assert motivo is not None
    assert fragmento in motivo


def test_quedarse_donde_esta_no_es_un_error() -> None:
    """Marcar «lista» dos veces no puede fallar: el tablero se toca con prisa."""
    assert motivo_si_no_puede("ready", "ready") is None
