"""directed river network relationships

Revision ID: 0012_river_networks
Revises: 0011_linear_area_features
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_river_networks"
down_revision = "0011_linear_area_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("map_features") as batch:
        batch.add_column(sa.Column("downstream_feature_type", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("downstream_feature_id", sa.Integer(), nullable=True))
        batch.create_index("ix_map_features_downstream_feature_type", ["downstream_feature_type"])
        batch.create_index("ix_map_features_downstream_feature_id", ["downstream_feature_id"])


def downgrade() -> None:
    with op.batch_alter_table("map_features") as batch:
        batch.drop_index("ix_map_features_downstream_feature_id")
        batch.drop_index("ix_map_features_downstream_feature_type")
        batch.drop_column("downstream_feature_id")
        batch.drop_column("downstream_feature_type")
