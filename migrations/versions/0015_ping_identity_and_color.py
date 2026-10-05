"""ping identity and persistent player color

Revision ID: 0015_ping_identity_color
Revises: 0014_expedition_ping_player_poi
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_ping_identity_color"
down_revision = "0014_expedition_ping_player_poi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ping_color", sa.String(length=7), nullable=False, server_default="#ff4f64"))
    op.add_column("expeditions", sa.Column("ping_user_id", sa.Integer(), nullable=True))
    op.add_column("expeditions", sa.Column("ping_created_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_expeditions_ping_user_id", "expeditions", ["ping_user_id"], unique=False)
    op.create_foreign_key("fk_expeditions_ping_user", "expeditions", "users", ["ping_user_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_expeditions_ping_user", "expeditions", type_="foreignkey")
    op.drop_index("ix_expeditions_ping_user_id", table_name="expeditions")
    op.drop_column("expeditions", "ping_created_at")
    op.drop_column("expeditions", "ping_user_id")
    op.drop_column("users", "ping_color")
