from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.identity.models import Address, Customer, CustomerPreference
from app.shared.db import BaseModel, TimestampMixin
from app.shared.db.settings import DatabaseSettings

# Ensure all identity models are registered on the metadata before autogenerate.
_ = (Customer, Address, CustomerPreference, TimestampMixin)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = DatabaseSettings()  # type: ignore[call-arg]
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = BaseModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode.

    Configures the context with just a URL and no Engine. Migrations are
    emitted to the script output rather than executed against a live database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode.

    Creates an Engine and associates a connection with the context before
    running migrations against the live database.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
