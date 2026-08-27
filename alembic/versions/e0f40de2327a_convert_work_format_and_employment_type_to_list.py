# mypy: ignore-errors

"""
Convert work format and employment type to list

Revision ID: e0f40de2327a
Revises: d32bd195d834
Create Date: 2026-05-04 15:46:21.087360
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.config import settings

revision: str = "e0f40de2327a"
down_revision: Union[str, Sequence[str], None] = "d32bd195d834"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

schema = settings.database_schema
table = f"{schema}.vacancies" if schema else "vacancies"
columns = (
    ("work_format", "work_formats"),
    ("employment_type", "employment_types"),
)


def upgrade() -> None:
    """Upgrade schema."""
    json_expr = "json_array" if settings.is_sqlite else "jsonb_build_array"
    for old_column, new_column in columns:
        op.add_column(
            "vacancies",
            sa.Column(new_column, sa.JSON(), nullable=True),
            schema=schema,
            if_not_exists=not settings.is_sqlite,
        )
        op.execute(f"""
            UPDATE {table}
            SET {new_column} =
                CASE
                    WHEN {old_column} IS NULL THEN NULL
                    ELSE {json_expr}({old_column})
                END
        """)
        op.drop_column(
            "vacancies",
            old_column,
            schema=schema,
            if_exists=not settings.is_sqlite,
        )


def downgrade() -> None:
    """Downgrade schema."""
    for old_column, new_column in columns:
        op.add_column(
            "vacancies",
            sa.Column(old_column, sa.VARCHAR(), nullable=True),
            schema=schema,
            if_not_exists=not settings.is_sqlite,
        )
        if settings.is_sqlite:
            json_expr = f"json_extract({new_column}, '$[0]')"
        else:
            json_expr = f"{new_column}->>0"
        op.execute(f"UPDATE {table} SET {old_column} = {json_expr}")

        op.drop_column(
            "vacancies",
            new_column,
            schema=schema,
            if_exists=not settings.is_sqlite,
        )
