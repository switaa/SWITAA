import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic import context
from sqlalchemy import create_engine

from app.core.database import Base
from app.models import *  # noqa: F401,F403 - import all models for autogenerate

config = context.config

database_url = os.getenv(
    "DATABASE_URL",
    config.get_main_option("sqlalchemy.url"),
)

target_metadata = Base.metadata


def run_migrations_online():
    engine = create_engine(database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
