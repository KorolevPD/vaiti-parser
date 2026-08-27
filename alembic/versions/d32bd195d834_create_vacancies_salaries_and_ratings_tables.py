# mypy: ignore-errors

"""
Create vacancies, salaries and ratings tables

Revision ID: d32bd195d834
Revises:
Create Date: 2026-04-09 12:44:46.924193
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

from app.core.config import settings

revision: str = "d32bd195d834"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

schema = settings.database_schema


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}") if schema else None

    op.create_table(
        "ratings",
        sa.Column(
            "company_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column(
            "company_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "source", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("reviews_count", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("company_name", "source"),
        schema=schema,
    )
    op.create_table(
        "salaries",
        sa.Column(
            "source", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "external_title",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column(
            "external_grade",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column(
            "external_specialization",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column("salary_min", sa.Integer(), nullable=False),
        sa.Column("salary_max", sa.Integer(), nullable=False),
        sa.Column(
            "currency", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column(
            "company_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column(
            "company_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column(
            "specialization_id",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column(
            "grade_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("source", "external_title", "external_grade"),
        schema=schema,
    )
    op.create_table(
        "vacancies",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "source", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "company_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column(
            "company_logo_url",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column(
            "position_title", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column(
            "raw_text", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "location", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("city", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "source_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "salary_raw", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column(
            "salary_currency",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("salary_gross", sa.Boolean(), nullable=True),
        sa.Column(
            "work_format", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column(
            "employment_type",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("published_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", "source"),
        schema=schema,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("vacancies", schema=schema, if_exists=True)
    op.drop_table("salaries", schema=schema, if_exists=True)
    op.drop_table("ratings", schema=schema, if_exists=True)
