"""persist map hex visibility score

Revision ID: 0005_map_hex_visibility
Revises: 0004_character_knowledge
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_map_hex_visibility"
down_revision = "0004_character_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "map_hexes",
        sa.Column("visibility_score", sa.Integer(), nullable=False, server_default="3"),
    )
    # Backfill existing persisted map versions from the built-in terrain rules.
    # Unknown/custom terrain keys keep the neutral default of 3.
    op.execute(
        sa.text(
            """
            UPDATE map_hexes
            SET visibility_score = CASE terrain_key
                WHEN 'PLAIN' THEN 3
                WHEN 'SEA' THEN 5
                WHEN 'SWAMP' THEN 2
                WHEN 'HILL' THEN 3
                WHEN 'FOREST' THEN 2
                WHEN 'DEEP_FOREST' THEN 2
                WHEN 'LOW_MOUNTAIN' THEN 5
                WHEN 'MOUNTAIN' THEN 6
                WHEN 'HIGH_MOUNTAIN' THEN 7
                ELSE 3
            END
            """
        )
    )


def downgrade() -> None:
    op.drop_column("map_hexes", "visibility_score")
