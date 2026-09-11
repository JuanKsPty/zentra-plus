"""
Lo que SQLite no puede probar.

La suite normal corre en memoria para que `pnpm test` funcione en una maquina
recien clonada, sin Docker. Pero hay garantias que SOLO existen contra
PostgreSQL, y probarlas sobre SQLite seria peor que no probarlas: daria verde
sin comprobar nada.

Estas se saltan si no hay base delante, y son obligatorias en el CI.
"""

import os
import pathlib
from collections.abc import Generator

import pytest
from sqlalchemy import text
from sqlmodel import Session, create_engine

URL = os.environ.get("TEST_DATABASE_URL", "")


def pytest_collection_modifyitems(items) -> None:
    """
    Marca como `pg` todo lo que viva en esta carpeta.

    Y NO con `pytestmark = pytest.mark.pg` a nivel de modulo, que es lo que
    parece que deberia funcionar: en un `conftest.py`, `pytestmark` solo afecta
    a las pruebas de ESE archivo, no a las de los modulos vecinos. Con esa
    version, `pytest -m pg` seleccionaba CERO casos y el trabajo del CI fallaba
    por no encontrar nada que correr — que es mejor que lo contrario, pero se
    tarda en entender.

    Asi, ademas, un archivo nuevo en esta carpeta no puede olvidarse la marca.
    """
    for item in items:
        if item.path.is_relative_to(pathlib.Path(__file__).parent):
            item.add_marker(pytest.mark.pg)


@pytest.fixture(scope="session", name="motor_pg")
def motor_pg_fixture():
    if not URL:
        pytest.skip("sin TEST_DATABASE_URL: se salta lo que necesita PostgreSQL")
    return create_engine(URL, pool_pre_ping=True)


@pytest.fixture(name="base_vacia")
def base_vacia_fixture(motor_pg) -> Generator[Session]:
    """
    Un esquema construido DESDE CERO por las migraciones, en cada caso.

    Es la unica forma de que «las migraciones funcionan» sea un hecho y no una
    esperanza: una base que se fue parcheando a mano durante meses puede
    funcionar perfectamente y no poder recrearse.
    """
    from alembic import command
    from alembic.config import Config

    with motor_pg.begin() as conexion:
        conexion.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conexion.execute(text("CREATE SCHEMA public"))

    configuracion = Config("alembic.ini")
    configuracion.set_main_option("sqlalchemy.url", URL)
    command.upgrade(configuracion, "head")

    with Session(motor_pg) as sesion:
        yield sesion
