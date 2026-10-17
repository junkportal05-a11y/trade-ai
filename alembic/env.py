"""Alembic environment configuration."""
from __future__ import with_statement

import os
import sys
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add backend to path for imports
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
sys.path.insert(0, backend_path)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# add your model's MetaData object here
# for 'autogenerate' support
from app.core.database import Base
target_metadata = Base.metadata

# Force SQLite for local alembic migrations (tests run against SQLite)
# Use the local trading_platform.db file
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "trading_platform.db"))
os.makedirs(os.path.dirname(db_path), exist_ok=True)
db_url = f"sqlite:///{db_path}"
config.set_main_option("sqlalchemy.url", db_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # example: http://stackoverflow.com/a/21642747/244029
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            # For SQLite in file mode, this ensures batch mode
            render_as_batch=True if config.get_main_option(
                "sqlalchemy.url").startswith('sqlite') else False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()