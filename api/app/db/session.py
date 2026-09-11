from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import settings


def _engine_kwargs() -> dict:
    if settings.database_kind == "sqlite":
        # SQLite necesita esto para que FastAPI pueda usar la conexion en
        # distintos hilos del threadpool.
        return {"connect_args": {"check_same_thread": False}}
    # pool_pre_ping evita el clasico "server closed the connection" cuando
    # Postgres estuvo un rato sin trafico. El tamano del pool se queda
    # holgadamente por debajo de los 40 hilos del threadpool de anyio, que es
    # quien atiende los endpoints sincronos: al reves, el cuello de botella se
    # invertiria y habria hilos esperando conexion.
    kwargs: dict = {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 10}

    if settings.usa_pooler:
        # Detras de pgbouncer en modo transaccion no se pueden usar sentencias
        # preparadas: psycopg las crea por nombre en la sesion y el pooler
        # devuelve cada sentencia a una sesion distinta, asi que la segunda vez
        # falla con "prepared statement ya existe". El sintoma es peor que el
        # fallo: funciona en las primeras peticiones y empieza a romper cuando
        # hay trafico, que es cuando el pooler empieza a reutilizar de verdad.
        kwargs["connect_args"] = {"prepare_threshold": None}

    return kwargs


# echo=False SIEMPRE, y no es una preferencia de ruido: el registro de
# sentencias de SQLAlchemy incluye los parametros enlazados, asi que un insert
# fallido en la tabla de usuarios dejaria el hash del PIN en `docker logs`.
engine = create_engine(settings.database_url, echo=False, **_engine_kwargs())


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
