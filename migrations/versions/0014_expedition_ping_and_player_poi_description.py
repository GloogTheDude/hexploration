"""expedition ping and player POI description

Revision ID: 0014_expedition_ping_player_poi
Revises: 0013_poi_hubs
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_expedition_ping_player_poi"
down_revision = "0013_poi_hubs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expeditions", sa.Column("ping_q", sa.Integer(), nullable=True))
    op.add_column("expeditions", sa.Column("ping_r", sa.Integer(), nullable=True))
    op.add_column("expeditions", sa.Column("ping_game_minute", sa.BigInteger(), nullable=True))
    op.add_column("points_of_interest", sa.Column("player_description", sa.Text(), nullable=True))
    op.add_column("points_of_interest", sa.Column("requires_discovery", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("points_of_interest", "requires_discovery")
    op.drop_column("points_of_interest", "player_description")
    op.drop_column("expeditions", "ping_game_minute")
    op.drop_column("expeditions", "ping_r")
    op.drop_column("expeditions", "ping_q")
