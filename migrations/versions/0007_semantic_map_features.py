"""Persist semantic feature identities across map versions.

Revision ID: 0007_semantic_map_features
Revises: 0006_character_map_knowledge
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_semantic_map_features"
down_revision = "0006_character_map_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "map_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("map_id", sa.Integer(), sa.ForeignKey("maps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_type", sa.String(length=80), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("campaign_id", "feature_type", "feature_id", name="uq_map_feature_campaign_type_id"),
    )
    op.create_index("ix_map_features_campaign_id", "map_features", ["campaign_id"])
    op.create_index("ix_map_features_map_id", "map_features", ["map_id"])
    op.create_index("ix_map_features_feature_type", "map_features", ["feature_type"])
    op.create_index("ix_map_features_feature_id", "map_features", ["feature_id"])

    op.add_column("points_of_interest", sa.Column("feature_id", sa.Integer(), nullable=True))
    op.create_index("ix_points_of_interest_feature_id", "points_of_interest", ["feature_id"])

    # Existing POI ids were already used as WorldEvent.target_id. Keep those
    # integers as their semantic ids so all historical events remain valid.
    op.execute("UPDATE points_of_interest SET feature_id = id WHERE feature_id IS NULL")

    op.execute("""
        INSERT INTO map_features (campaign_id, map_id, feature_type, feature_id, created_at)
        SELECT DISTINCT m.campaign_id, m.id, 'POI', p.feature_id, CURRENT_TIMESTAMP
        FROM points_of_interest p
        JOIN map_hexes h ON h.id = p.hex_id
        JOIN map_versions v ON v.id = h.map_version_id
        JOIN maps m ON m.id = v.map_id
    """)

    # MapEdge.feature_id was already designed as a semantic id. Register it.
    op.execute("""
        INSERT INTO map_features (campaign_id, map_id, feature_type, feature_id, created_at)
        SELECT DISTINCT m.campaign_id, m.id, e.feature_type, e.feature_id, CURRENT_TIMESTAMP
        FROM map_edges e
        JOIN map_versions v ON v.id = e.map_version_id
        JOIN maps m ON m.id = v.map_id
    """)

    with op.batch_alter_table("points_of_interest") as batch:
        batch.alter_column("feature_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.drop_index("ix_points_of_interest_feature_id", table_name="points_of_interest")
    with op.batch_alter_table("points_of_interest") as batch:
        batch.drop_column("feature_id")
    op.drop_table("map_features")
