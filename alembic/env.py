from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from dealarchive import models  # noqa: F401  (registers models on Base.metadata)
from dealarchive.config import settings
from dealarchive.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Note: settings.database_url may contain a literal "%" (percent-encoded
# password characters), which configparser's interpolation would choke on if
# routed through config.set_main_option. Build the engine directly instead.

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
