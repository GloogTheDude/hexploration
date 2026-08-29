"""Add immutable per-character map hex knowledge observations.

Revision ID: 0006_character_map_knowledge
Revises: 0005_map_hex_visibility
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_character_map_knowledge"
down_revision = "0005_map_hex_visibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_map_hex_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "character_id",
            sa.Integer(),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "expedition_id",
            sa.Integer(),
            sa.ForeignKey("expeditions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "map_id",
            sa.Integer(),
            sa.ForeignKey("maps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "map_version_id",
            sa.Integer(),
            sa.ForeignKey("map_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("q", sa.Integer(), nullable=False),
        sa.Column("r", sa.Integer(), nullable=False),
        sa.Column("observed_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("discovery_state", sa.String(length=20), nullable=False),
        sa.Column("terrain_key", sa.String(length=80), nullable=False),
        sa.Column("elevation", sa.Integer(), nullable=False),
        sa.Column("visibility_score", sa.Integer(), nullable=False),
        sa.Column("extra_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "observed_game_minute >= 0",
            name="ck_character_map_hex_observed_minute_positive",
        ),
        sa.UniqueConstraint(
            "character_id",
            "map_id",
            "q",
            "r",
            "observed_game_minute",
            "expedition_id",
            name="uq_character_map_hex_observation",
        ),
    )
    for column in (
        "character_id",
        "expedition_id",
        "map_id",
        "map_version_id",
        "q",
        "r",
        "observed_game_minute",
    ):
        op.create_index(
            f"ix_character_map_hex_observations_{column}",
            "character_map_hex_observations",
            [column],
        )


def downgrade() -> None:
    op.drop_table("character_map_hex_observations")
