from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registra los modelos en SQLModel.metadata)
from app.core.config import settings

config = context.config

# La URL sale de settings, no de alembic.ini: una sola fuente de verdad, y asi
# los comandos del host y los de dentro del contenedor no pueden divergir.
#
# Y es `migration_url`, no `database_url`: en produccion la aplicacion habla por
# el pooler de Supabase y las migraciones tienen que ir por la conexion directa.
#
# Salvo que QUIEN LLAMA ya haya puesto una. Sin este `if`, una prueba que apunta
# Alembic a una base desechable acaba migrando la de desarrollo y comprobando
# otra cosa distinta de la que cree.
if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", settings.migration_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


# Indices que existen en la base pero NO en los modelos, porque SQLAlchemy no
# sabe expresarlos: los que van sobre una expresion en vez de sobre columnas.
#
# Van aqui con nombre y uno a uno. Sin esta lista, `autogenerate` los ve en la
# base, no los encuentra en el metadata y propone BORRARLOS — y una revision que
# elimina en silencio la garantia de fila unica de la configuracion es
# exactamente el tipo de cambio que nadie revisa dos veces.
INDICES_ESCRITOS_A_MANO = {
    "uq_business_config_fila_unica",
}


def incluir_objeto(objeto, nombre, tipo, reflejado, comparar_con) -> bool:
    """
    Que queda fuera del autogenerate.

    Dos clases de indice, y las dos por el mismo motivo de fondo: Alembic no
    puede compararlos de forma fiable con lo que hay en la base.

    1. Los que van sobre una EXPRESION (`((true))`). No existen en el metadata,
       asi que los propondria para borrar.
    2. Los PARCIALES (`WHERE ...`). Alembic no compara `postgresql_where` contra
       lo reflejado, asi que saldria un DROP/CREATE espurio en cada revision o,
       peor, no los veria y propondria un duplicado con otro nombre.

    Los parciales SI se declaran en el modelo —para que las tablas de desarrollo
    y las de los tests los tengan— y ademas se escriben a mano en la migracion,
    con el mismo nombre.
    """
    if tipo != "index":
        return True

    if nombre in INDICES_ESCRITOS_A_MANO:
        return False

    if getattr(objeto, "dialect_options", None):
        parcial = objeto.dialect_options.get("postgresql", {}).get("where")
        if parcial is not None:
            return False

    return True


def migraciones_sin_conexion() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url") or settings.migration_url,
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
            render_as_batch=conexion.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    migraciones_sin_conexion()
else:
    migraciones_con_conexion()
