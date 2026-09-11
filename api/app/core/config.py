from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuracion de la API. Se lee del .env de la RAIZ del proyecto
    (../.env cuando se corre desde api/) y, si existe, de un api/.env que
    tiene prioridad. En Docker las variables llegan del entorno.
    """

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Zentra+"
    app_version: str = "0.1.0"
    app_env: str = "dev"

    # Zona horaria del negocio. Manda en todo calculo por dia: un reporte "de
    # hoy" se corta a medianoche AQUI, no en la del servidor. Los runners de CI
    # van en UTC y sin esto el desfase es invisible hasta que descuadra un turno.
    timezone: str = "America/Panama"

    # ---- Base de datos -------------------------------------------------
    # La que usa la aplicacion. En desarrollo, el Postgres de docker compose;
    # en produccion, el pooler de Supabase.
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/zentra"

    # La que usan las migraciones. Vacia = la misma que la aplicacion, que es lo
    # normal en desarrollo. En produccion tiene que ser la conexion DIRECTA de
    # Supabase: el pooler en modo transaccion no mantiene la sesion entre
    # sentencias, y una migracion necesita bloqueos que viven en la sesion.
    direct_url: str = ""

    # ---- Seguridad -----------------------------------------------------
    # Sin valor utilizable por defecto: es mejor no arrancar que firmar con un
    # secreto que esta publicado en el repositorio.
    jwt_secret: str = ""
    jwt_refresh_secret: str = ""

    # ---- CORS ----------------------------------------------------------
    # Se deja como str y no como list[str] a proposito: pydantic-settings
    # intenta parsear las listas como JSON y "a,b" haria estallar el arranque.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ---- Registro ------------------------------------------------------
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]

    @property
    def database_kind(self) -> str:
        return "sqlite" if self.database_url.startswith("sqlite") else "postgresql"

    @property
    def migration_url(self) -> str:
        """La URL con la que corre Alembic. Ver `direct_url`."""
        return self.direct_url.strip() or self.database_url

    @property
    def usa_pooler(self) -> bool:
        """
        Si la conexion va por pgbouncer en modo transaccion.

        Importa porque ahi hay que apagar las sentencias preparadas: psycopg las
        crea por nombre en la sesion, y el pooler devuelve cada sentencia a una
        sesion distinta, asi que la segunda vez falla con "prepared statement
        ya existe". Se detecta por la forma de la URL en vez de por otra
        variable, para que no haya dos cosas que puedan discrepar.
        """
        return "pooler." in self.database_url or ":6543/" in self.database_url

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() in {"dev", "development", "local", "test"}

    @model_validator(mode="after")
    def _exigir_secretos_propios(self) -> "Settings":
        """
        Fuera de desarrollo la API se niega a arrancar sin secretos de verdad.

        El ultimo caso es el menos obvio de los tres y el mas grave: con el mismo
        secreto para acceso y refresco, un token de acceso vale como token de
        refresco y la rotacion deja de significar nada.
        """
        if self.is_dev:
            return self
        for nombre in ("jwt_secret", "jwt_refresh_secret"):
            valor: str = getattr(self, nombre)
            if not valor or valor.startswith("cambia-esto"):
                raise ValueError(
                    f"{nombre.upper()} tiene que fijarse fuera de desarrollo. "
                    "Generalo con: openssl rand -hex 32"
                )
        if self.jwt_secret == self.jwt_refresh_secret:
            raise ValueError("JWT_SECRET y JWT_REFRESH_SECRET tienen que ser distintos")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
