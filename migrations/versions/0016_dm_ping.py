"""independent DM expedition ping

Revision ID: 0016_dm_ping
Revises: 0015_ping_identity_color
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_dm_ping"
down_revision = "0015_ping_identity_color"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("expeditions", sa.Column("dm_ping_q", sa.Integer(), nullable=True))
    op.add_column("expeditions", sa.Column("dm_ping_r", sa.Integer(), nullable=True))
    op.add_column("expeditions", sa.Column("dm_ping_game_minute", sa.BigInteger(), nullable=True))
    op.add_column("expeditions", sa.Column("dm_ping_user_id", sa.Integer(), nullable=True))
    op.add_column("expeditions", sa.Column("dm_ping_created_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_expeditions_dm_ping_user_id", "expeditions", ["dm_ping_user_id"], unique=False)
    op.create_foreign_key("fk_expeditions_dm_ping_user", "expeditions", "users", ["dm_ping_user_id"], ["id"], ondelete="SET NULL")

def downgrade() -> None:
    op.drop_constraint("fk_expeditions_dm_ping_user", "expeditions", type_="foreignkey")
    op.drop_index("ix_expeditions_dm_ping_user_id", table_name="expeditions")
    op.drop_column("expeditions", "dm_ping_created_at")
    op.drop_column("expeditions", "dm_ping_user_id")
    op.drop_column("expeditions", "dm_ping_game_minute")
    op.drop_column("expeditions", "dm_ping_r")
    op.drop_column("expeditions", "dm_ping_q")
