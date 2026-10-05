"""mark POIs as expedition hubs

Revision ID: 0013_poi_hubs
Revises: 0012_river_networks
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_poi_hubs"
down_revision = "0012_river_networks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("points_of_interest") as batch:
        batch.add_column(sa.Column("is_hub", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_index("ix_points_of_interest_is_hub", ["is_hub"])


def downgrade() -> None:
    with op.batch_alter_table("points_of_interest") as batch:
        batch.drop_index("ix_points_of_interest_is_hub")
        batch.drop_column("is_hub")
