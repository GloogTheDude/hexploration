"""Add persistent map edges for temporal traversal rules.

Revision ID: 0003_map_edges
Revises: 0002_exp_weather_transport
Create Date: 2026-08-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_map_edges"
down_revision: Union[str, None] = "0002_exp_weather_transport"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "map_edges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("map_version_id", sa.Integer(), nullable=False),
        sa.Column("from_q", sa.Integer(), nullable=False),
        sa.Column("from_r", sa.Integer(), nullable=False),
        sa.Column("to_q", sa.Integer(), nullable=False),
        sa.Column("to_r", sa.Integer(), nullable=False),
        sa.Column("feature_type", sa.String(length=80), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "feature_id > 0",
            name="ck_map_edge_feature_id_positive",
        ),
        sa.ForeignKeyConstraint(
            ["map_version_id"],
            ["map_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "map_version_id",
            "from_q",
            "from_r",
            "to_q",
            "to_r",
            name="uq_map_edge_coordinates",
        ),
    )
    op.create_index(
        op.f("ix_map_edges_map_version_id"),
        "map_edges",
        ["map_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_map_edges_feature_type"),
        "map_edges",
        ["feature_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_map_edges_feature_id"),
        "map_edges",
        ["feature_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_map_edges_feature_id"), table_name="map_edges")
    op.drop_index(op.f("ix_map_edges_feature_type"), table_name="map_edges")
    op.drop_index(op.f("ix_map_edges_map_version_id"), table_name="map_edges")
    op.drop_table("map_edges")
