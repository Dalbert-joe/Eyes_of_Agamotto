from logging.config import fileConfig
import os
from alembic import context
from app.database import Base
from app import models  # noqa: F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline():
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    from sqlalchemy import engine_from_config
    from sqlalchemy.pool import NullPool
    cfg = dict(config.get_section(config.config_ini_section) or {})
    cfg["sqlalchemy.url"] = os.getenv("DATABASE_URL", cfg.get("sqlalchemy.url"))
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
