"""Add DB-backed, versioned character sheet form data.

Revision ID: 0009_character_sheet_data
Revises: 0008_campaign_invitations
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_character_sheet_data"
down_revision = "0008_campaign_invitations"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "character_sheet_data_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("campaign_game_minute", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("character_id", "version", name="uq_character_sheet_data_version"),
    )
    op.create_index("ix_character_sheet_data_versions_character_id", "character_sheet_data_versions", ["character_id"])


def downgrade():
    op.drop_index("ix_character_sheet_data_versions_character_id", table_name="character_sheet_data_versions")
    op.drop_table("character_sheet_data_versions")
