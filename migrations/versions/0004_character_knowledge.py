"""Add immutable character knowledge observations.

Revision ID: 0004_character_knowledge
Revises: 0003_map_edges
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_character_knowledge"
down_revision = "0003_map_edges"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_knowledge_observations",
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
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("observed_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("knowledge", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "observed_game_minute >= 0",
            name="ck_character_knowledge_observed_minute_positive",
        ),
        sa.UniqueConstraint(
            "character_id",
            "target_type",
            "target_id",
            "observed_game_minute",
            "expedition_id",
            name="uq_character_knowledge_observation",
        ),
    )
    op.create_index(
        "ix_character_knowledge_observations_character_id",
        "character_knowledge_observations",
        ["character_id"],
    )
    op.create_index(
        "ix_character_knowledge_observations_expedition_id",
        "character_knowledge_observations",
        ["expedition_id"],
    )
    op.create_index(
        "ix_character_knowledge_observations_target_type",
        "character_knowledge_observations",
        ["target_type"],
    )
    op.create_index(
        "ix_character_knowledge_observations_target_id",
        "character_knowledge_observations",
        ["target_id"],
    )
    op.create_index(
        "ix_character_knowledge_observations_observed_game_minute",
        "character_knowledge_observations",
        ["observed_game_minute"],
    )


def downgrade() -> None:
    op.drop_table("character_knowledge_observations")
