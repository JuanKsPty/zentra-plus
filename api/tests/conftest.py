"""
Arnes de pruebas.

La suite corre sobre SQLite en memoria para que no dependa de Docker: `pnpm test`
tiene que funcionar en una maquina recien clonada. Lo que SQLite NO puede probar
—indices parciales bajo concurrencia, numeric de verdad, el esquema construido
desde cero— va marcado con @pytest.mark.pg y corre contra PostgreSQL en el CI.

LA SUITE NO DEPENDE DE NINGUN .env, y eso hay que forzarlo. `Settings` lee el
`.env` de la raiz, asi que sin estas lineas las pruebas pasan en la maquina de
quien ya tiene secretos configurados y FALLAN en el CI, donde no hay `.env` y
pyjwt se niega a firmar con una clave vacia. Una suite que da un resultado
distinto segun el entorno de cada uno no prueba nada estable.

Se ponen ANTES de importar nada de `app`: `settings` es un singleton que se crea
al importar `app.core.config`, asi que despues ya seria tarde.
"""

import os

os.environ.setdefault("APP_ENV", "test")
os.environ["JWT_SECRET"] = "secreto-de-pruebas-no-usar-fuera-de-aqui-0001"
os.environ["JWT_REFRESH_SECRET"] = "secreto-de-refresco-de-pruebas-distinto-0002"
# Sin esto, una maquina con el .env apuntando a PostgreSQL haria que las pruebas
# en memoria intentaran hablar con una base que no tiene por que estar levantada.
os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel, create_engine  # noqa: E402

from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402


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


@pytest.fixture(name="client_sin_relanzar")
def client_sin_relanzar_fixture(session: Session) -> Generator[TestClient]:
    """
    Como `client`, pero deja que el manejador del 500 haga su trabajo.

    Por defecto TestClient relanza las excepciones del servidor, que es lo comodo
    para depurar pero hace imposible comprobar que un error no previsto sale con
    el sobre de la casa y sin filtrar nada. Con esto se ejercita el camino real.
    """
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
