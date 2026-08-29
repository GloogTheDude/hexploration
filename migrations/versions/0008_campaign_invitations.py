"""Add campaign invitation acceptance flow.

Revision ID: 0008_campaign_invitations
Revises: 0007_semantic_map_features
"""
from alembic import op
import sqlalchemy as sa
revision="0008_campaign_invitations"
down_revision="0007_semantic_map_features"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("campaign_invitations",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("campaign_id",sa.Integer(),sa.ForeignKey("campaigns.id",ondelete="CASCADE"),nullable=False),
        sa.Column("invited_user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("invited_by_user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("status",sa.String(length=20),nullable=False,server_default="PENDING"),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("responded_at",sa.DateTime(timezone=True),nullable=True),
        sa.UniqueConstraint("campaign_id","invited_user_id",name="uq_campaign_invitation_user"))
    for c in ("campaign_id","invited_user_id","invited_by_user_id","status"): op.create_index(f"ix_campaign_invitations_{c}","campaign_invitations",[c])
def downgrade(): op.drop_table("campaign_invitations")
