"""
Reconocer un choque de escrituras simultaneas.

Importa porque la respuesta correcta a un choque casi nunca es un 500. Dos
dispositivos que envian la misma comanda a la vez no son un fallo del sistema:
uno gana, y al otro hay que devolverle la comanda que gano, no un error.

LA REGLA: SE MIRA EL SQLSTATE, NUNCA EL TEXTO

Los mensajes de PostgreSQL estan traducidos segun `lc_messages`. Un
`/duplicate key/i` funciona hasta el dia que la base habla espanol y entonces
deja de reconocer nada, en silencio y solo en produccion. El SQLSTATE es un
codigo de cinco caracteres que no cambia nunca.
"""

from sqlalchemy.exc import DBAPIError

# 23505 unique_violation       — dos escrituras con la misma clave
# 40P01 deadlock_detected      — dos transacciones tomaron cerrojos en distinto
#                                orden; pasa de verdad cuando cada una inserta
#                                tambien las filas hijas
# 40001 serialization_failure  — la transaccion no se pudo serializar
SQLSTATES_DE_CONFLICTO = frozenset({"23505", "40P01", "40001"})


def sqlstate(error: BaseException) -> str | None:
    """El codigo SQLSTATE de un error de base de datos, si lo tiene."""
    original = getattr(error, "orig", None)
    if original is None:
        return None
    # psycopg 3 lo expone como `sqlstate`. `pgcode` es de psycopg 2 y aqui no
    # existe; buscarlo devolveria None siempre y el conflicto pasaria como 500.
    codigo = getattr(original, "sqlstate", None)
    return str(codigo) if codigo else None


def es_conflicto_concurrente(error: BaseException) -> bool:
    """
    Si el error viene de que alguien mas escribio a la vez.

    Cuando esto es cierto, reintentar o devolver lo que escribio el otro suele
    ser lo correcto. Un 500 no lo es: para una cola de reenvios un 500 es un
    fallo definitivo, asi que la operacion acabaria en la bandeja de fallos
    HABIENDO SIDO APLICADA.
    """
    if not isinstance(error, DBAPIError):
        return False
    return sqlstate(error) in SQLSTATES_DE_CONFLICTO


def restriccion_violada(error: BaseException) -> str | None:
    """
    El nombre del indice o la restriccion que se violo.

    Es lo que permite traducir «un turno abierto por cajero y sucursal» a su
    mensaje propio sin confundirlo con cualquier otro choque de unicidad. Se
    identifica por nombre y no por el texto del error, por lo mismo de arriba.
    """
    original = getattr(error, "orig", None)
    diagnostico = getattr(original, "diag", None)
    return getattr(diagnostico, "constraint_name", None) if diagnostico else None


def describir(error: BaseException) -> dict[str, str | None]:
    """
    Los campos de una excepcion de base de datos que SI se pueden registrar.

    Elegidos uno a uno, y esto no es exceso de celo. `str()` de un error de
    SQLAlchemy anade `[parameters: (...)]` con los valores enlazados, y el
    `message_detail` de psycopg lleva los valores de la fila que choco: un
    insert fallido en la tabla de usuarios pondria un hash de credencial en
    `docker logs`. Con el nombre de la restriccion y la tabla se diagnostica
    igual de bien; con los valores, no hace falta.
    """
    original = getattr(error, "orig", None)
    diagnostico = getattr(original, "diag", None)
    return {
        "type": type(error).__name__,
        "sqlstate": sqlstate(error),
        "constraint": getattr(diagnostico, "constraint_name", None) if diagnostico else None,
        "table": getattr(diagnostico, "table_name", None) if diagnostico else None,
        # message_primary es la frase del error. message_detail NO: ahi es donde
        # PostgreSQL escribe los valores de la fila.
        "primary": getattr(diagnostico, "message_primary", None) if diagnostico else None,
    }


def traducir(
    error: BaseException,
    por_restriccion: dict[str, tuple[str, str]],
    *,
    por_defecto: tuple[str, str] = (
        "conflicto",
        "Ya existe algo con esos datos.",
    ),
) -> tuple[str, str]:
    """
    Convierte una violacion de integridad en un error de negocio.

    Se intenta primero por NOMBRE de restriccion, que es lo que permite dar un
    mensaje concreto («ya hay una mesa 7 aqui») en vez de uno generico. Pero el
    nombre solo lo da PostgreSQL: SQLite no expone diagnostico, asi que en las
    pruebas en memoria no hay forma de saber cual choco.

    Por eso hay un caso por defecto. Sin el, la misma carrera que en PostgreSQL
    sale como un 409 legible saldria como un 500 en cualquier otro motor — y un
    500 es, ademas, un fallo definitivo para una cola de reenvios.
    """
    nombre = restriccion_violada(error)
    if nombre and nombre in por_restriccion:
        return por_restriccion[nombre]
    return por_defecto
