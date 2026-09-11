"""
Arnes de pruebas.

La suite corre sobre SQLite en memoria para que no dependa de Docker: `pnpm test`
tiene que funcionar en una maquina recien clonada. Lo que SQLite NO puede probar
—indices parciales bajo concurrencia, unaccent, numeric de verdad— va marcado
con @pytest.mark.pg y corre contra Postgres en el CI.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db.session import get_session
from app.main import app


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session]:
    # StaticPool: sin el, cada conexion abriria SU PROPIA base en memoria y las
    # tablas creadas aqui no existirian para la peticion de al lado.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    # Sin `with`: asi no se ejecuta el lifespan, que no hace falta y que
    # intentaria hablar con una base que en los tests no existe.
    yield TestClient(app)
    app.dependency_overrides.clear()
