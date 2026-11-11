import sys
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlmodel import SQLModel

from alembic import context

# Aseguramos que la raíz del proyecto (donde está main.py) esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Reutilizamos el mismo engine que usa tu app (ya lee el .env y arregla la URL)
from db.database import engine
from db import models  # noqa: asegura que todas las clases se registren en el metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()