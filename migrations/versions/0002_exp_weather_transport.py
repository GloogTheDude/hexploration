"""Persist expedition weather and transport.

Revision ID: 0002_exp_weather_transport
Revises: 0001_initial_schema
Create Date: 2026-08-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_exp_weather_transport"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expeditions",
        sa.Column("weather_key", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "expeditions",
        sa.Column("transport_key", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("expeditions", "transport_key")
    op.drop_column("expeditions", "weather_key")
