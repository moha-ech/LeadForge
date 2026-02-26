"""
Configuración de Alembic para migraciones de base de datos.

Conecta Alembic con nuestros modelos SQLAlchemy y la configuración
del proyecto para que sepa qué tablas crear/modificar.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.config import get_settings

# Importar TODOS los modelos aquí para que Alembic los detecte.
# Si creas un modelo nuevo y no lo importas aquí, Alembic no lo verá.
from app.models.base import Base
from app.models.lead import Company, Lead, LeadEvent 

# Configuración de Alembic (lee alembic.ini)
config = context.config

# Configurar logging desde alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Decirle a Alembic cuál es el "estado deseado" de la BD.
# Alembic compara esto con el estado actual y genera la migración.
target_metadata = Base.metadata

# Obtener URL de conexión desde nuestra configuración
settings = get_settings()

# Alembic usa conexión SÍNCRONA (no async), así que
# cambiamos asyncpg por psycopg2
sync_database_url = settings.database_url.replace(
    "postgresql+asyncpg", "postgresql+psycopg2"
)


def run_migrations_offline() -> None:
    """Genera SQL sin conectarse a la BD (modo offline)."""
    context.configure(
        url=sync_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones conectándose a la BD (modo normal)."""
    engine = create_engine(sync_database_url)

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()