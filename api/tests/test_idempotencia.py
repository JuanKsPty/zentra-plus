from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.conflicts import describir, es_conflicto_concurrente, restriccion_violada, sqlstate
from app.core.occurred_at import resolver
from app.core.schemas import ConClaveDeReenvio, ConHoraDelHecho, ConIdDelCliente, Entrada

AHORA = datetime(2026, 9, 11, 20, 0, tzinfo=UTC)


class _Diagnostico:
    constraint_name = "idx_shifts_un_abierto_por_cajero_y_sucursal"
    table_name = "shifts"
    message_primary = "llave duplicada viola restriccion de unicidad"
    # Aqui es donde PostgreSQL escribe los VALORES de la fila que choco.
    message_detail = "Ya existe la llave (opened_by)=(a3f0e61c-...)."


class _ErrorDePsycopg(Exception):
    sqlstate = "23505"
    diag = _Diagnostico()


def _integrity_error() -> IntegrityError:
    return IntegrityError("INSERT INTO shifts ...", {"pin": "$argon2id$secreto"}, _ErrorDePsycopg())


# --- reconocer un choque ----------------------------------------------------


def test_una_violacion_de_unicidad_es_un_conflicto() -> None:
    assert es_conflicto_concurrente(_integrity_error()) is True
    assert sqlstate(_integrity_error()) == "23505"


@pytest.mark.parametrize("codigo", ["40P01", "40001"])
def test_un_interbloqueo_tambien_lo_es(codigo: str) -> None:
    """
    No solo la unicidad.

    Dos reenvios simultaneos insertan tambien las filas hijas y toman los
    cerrojos en distinto orden, asi que el choque llega como interbloqueo.
    Tratarlo como fallo definitivo manda a la bandeja de errores una comanda
    que SI se creo.
    """
    original = type("Err", (Exception,), {"sqlstate": codigo, "diag": None})()
    assert es_conflicto_concurrente(OperationalError("...", {}, original)) is True


def test_un_error_cualquiera_no_es_un_conflicto() -> None:
    assert es_conflicto_concurrente(ValueError("nada que ver")) is False
    otro = type("Err", (Exception,), {"sqlstate": "23503", "diag": None})()
    assert es_conflicto_concurrente(IntegrityError("...", {}, otro)) is False


def test_se_reconoce_la_restriccion_por_nombre_no_por_el_texto() -> None:
    """
    Los mensajes de PostgreSQL estan traducidos segun `lc_messages`.

    Un `/duplicate key/i` funciona hasta que la base habla espanol —como en el
    error de esta prueba— y entonces deja de reconocer nada, en silencio y solo
    en produccion.
    """
    assert restriccion_violada(_integrity_error()) == (
        "idx_shifts_un_abierto_por_cajero_y_sucursal"
    )


def test_lo_que_se_registra_no_incluye_valores() -> None:
    descripcion = describir(_integrity_error())

    assert descripcion["sqlstate"] == "23505"
    assert descripcion["table"] == "shifts"
    assert descripcion["constraint"] == "idx_shifts_un_abierto_por_cajero_y_sucursal"

    # Ni los parametros enlazados ni el detalle de la fila: ahi es donde viajan
    # los valores, y uno de ellos puede ser un hash de credencial.
    volcado = str(descripcion)
    assert "argon2" not in volcado
    assert "a3f0e61c" not in volcado


# --- la hora del dispositivo ------------------------------------------------


def test_sin_hora_del_dispositivo_manda_la_del_servidor() -> None:
    assert resolver(None, ahora=AHORA) == AHORA


def test_una_hora_creible_se_respeta() -> None:
    hace_diez_minutos = AHORA - timedelta(minutes=10)
    assert resolver(hace_diez_minutos, ahora=AHORA) == hace_diez_minutos


def test_una_hora_del_futuro_se_descarta() -> None:
    """Sin esto, una tableta con el reloj adelantado clava su comanda arriba del
    tablero de cocina para siempre."""
    assert resolver(AHORA + timedelta(hours=3), ahora=AHORA) == AHORA


def test_una_hora_demasiado_vieja_se_descarta() -> None:
    """Un reloj sin configurar mandaria la comanda al fondo, donde nadie la ve."""
    assert resolver(AHORA - timedelta(days=400), ahora=AHORA) == AHORA


def test_una_hora_sin_zona_se_asume_en_utc_y_no_revienta() -> None:
    sin_zona = datetime(2026, 9, 11, 19, 55)
    assert resolver(sin_zona, ahora=AHORA) == sin_zona.replace(tzinfo=UTC)


def test_resolver_nunca_lanza() -> None:
    """Una hora absurda no puede costar una comanda."""
    for candidata in (datetime.min.replace(tzinfo=UTC), datetime.max.replace(tzinfo=UTC)):
        assert resolver(candidata, ahora=AHORA) == AHORA


# --- las bases de los cuerpos de entrada ------------------------------------


def test_un_campo_no_declarado_se_rechaza() -> None:
    class Cuerpo(Entrada):
        nombre: str

    with pytest.raises(ValidationError):
        Cuerpo(nombre="mesa 4", precio=3)  # type: ignore[call-arg]


def test_los_campos_de_reenvio_existen_desde_ya() -> None:
    """
    Aunque el modo sin conexion sea de una fase posterior.

    Con `extra="forbid"`, un campo no declarado da 422, y para una cola de
    reenvios un 422 es DEFINITIVO: no se reintenta. Declararlos hoy cuesta cero
    y evita perder una comanda por un sello de hora.
    """

    class CuerpoDeComanda(Entrada, ConIdDelCliente, ConHoraDelHecho):
        mesa: int

    cuerpo = CuerpoDeComanda.model_validate(
        {
            "mesa": 4,
            "id": "0199e1d9-1a2b-7c3d-8e4f-5a6b7c8d9e0f",
            "occurred_at": "2026-09-11T19:55:00Z",
        }
    )
    assert cuerpo.occurred_at is not None
    assert cuerpo.id is not None

    class CuerpoDeCobro(Entrada, ConClaveDeReenvio, ConHoraDelHecho):
        importe: int

    assert CuerpoDeCobro(importe=100, client_request_id="abc").client_request_id == "abc"
