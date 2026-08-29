"""Initial Hexploration relational schema.

Revision ID: 0001_initial_schema
Revises: None
"""
from alembic import op

from db import Base
from db import models  # noqa: F401

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Greenfield baseline. Future revisions should be generated with
    # `alembic revision --autogenerate -m "..."`.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
