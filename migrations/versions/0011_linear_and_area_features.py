"""linear and area map features

Revision ID: 0011_linear_area_features
Revises: 0010_sparse_map_versions
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_linear_area_features"
down_revision = "0010_sparse_map_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("map_edges") as batch:
        batch.drop_constraint("uq_map_edge_coordinates", type_="unique")
        batch.add_column(sa.Column("segment_index", sa.Integer(), nullable=False, server_default="0"))
        batch.create_unique_constraint(
            "uq_map_edge_feature_coordinates",
            ["map_version_id", "from_q", "from_r", "to_q", "to_r", "feature_type", "feature_id"],
        )

    op.create_table(
        "map_areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("map_version_id", sa.Integer(), sa.ForeignKey("map_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_type", sa.String(length=80), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=True),
        sa.Column("cells", sa.JSON(), nullable=False),
        sa.Column("extra_data", sa.JSON(), nullable=False),
        sa.CheckConstraint("feature_id > 0", name="ck_map_area_feature_id_positive"),
        sa.UniqueConstraint("map_version_id", "feature_type", "feature_id", name="uq_map_area_feature"),
    )
    op.create_index("ix_map_areas_map_version_id", "map_areas", ["map_version_id"])
    op.create_index("ix_map_areas_feature", "map_areas", ["feature_type", "feature_id"])


def downgrade() -> None:
    op.drop_index("ix_map_areas_feature", table_name="map_areas")
    op.drop_index("ix_map_areas_map_version_id", table_name="map_areas")
    op.drop_table("map_areas")
    with op.batch_alter_table("map_edges") as batch:
        batch.drop_constraint("uq_map_edge_feature_coordinates", type_="unique")
        batch.drop_column("segment_index")
        batch.create_unique_constraint(
            "uq_map_edge_coordinates",
            ["map_version_id", "from_q", "from_r", "to_q", "to_r"],
        )
