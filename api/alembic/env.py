from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registra los modelos en SQLModel.metadata)
from alembic import context
from app.core.config import settings

config = context.config

# La URL sale de settings, no de alembic.ini: una sola fuente de verdad, y asi
# los comandos del host y los de dentro del contenedor no pueden divergir.
#
# Y es `migration_url`, no `database_url`: en produccion la aplicacion habla por
# el pooler de Supabase y las migraciones tienen que ir por la conexion directa.
config.set_main_option("sqlalchemy.url", settings.migration_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def incluir_objeto(objeto, nombre, tipo, reflejado, comparar_con) -> bool:
    """
    Los indices PARCIALES se mantienen a mano y quedan fuera del autogenerate.

    Alembic no compara `postgresql_where` contra lo reflejado de forma fiable:
    el resultado es un DROP/CREATE espurio en cada revision o, peor, que no lo
    vea y proponga un duplicado con otro nombre. Se declaran en el modelo (para
    que las tablas de desarrollo y las de los tests los tengan) y se escriben a
    mano en la migracion, con el mismo nombre.
    """
    if tipo == "index" and getattr(objeto, "dialect_options", None):
        parcial = objeto.dialect_options.get("postgresql", {}).get("where")
        if parcial is not None:
            return False
    return True


def migraciones_sin_conexion() -> None:
    context.configure(
        url=settings.migration_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=incluir_objeto,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def migraciones_con_conexion() -> None:
    conectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conectable.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=target_metadata,
            include_object=incluir_objeto,
            compare_type=True,
            compare_server_default=True,
            # Solo tiene efecto en SQLite, que no sabe hacer ALTER de columnas.
            render_as_batch=settings.database_kind == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    migraciones_sin_conexion()
else:
    migraciones_con_conexion()
