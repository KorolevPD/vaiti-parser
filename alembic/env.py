from typing import Optional

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.schema import SchemaItem
from sqlmodel import SQLModel

from app.core.config import settings
import app.models  # noqa: F401

target_metadata = SQLModel.metadata


def include_object(
    object: SchemaItem,
    name: Optional[str],
    type_: str,
    reflected: bool,
    compare_to: Optional[SchemaItem],
) -> bool:
    if type_ == "table" and name == "apscheduler_jobs":
        return False
    return True


def run_migrations_offline() -> None:
    """Запуск миграций в offline-режиме."""

    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema=settings.database_schema,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в online-режиме."""

    connectable = create_engine(settings.DATABASE_URL, echo=True)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=settings.database_schema,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
