"""Add sparse map version default terrain.

Revision ID: 0010_sparse_map_versions
Revises: 0009_character_sheet_data
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_sparse_map_versions"
down_revision = "0009_character_sheet_data"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("map_versions", sa.Column("default_terrain_key", sa.String(length=80), nullable=True))

def downgrade():
    op.drop_column("map_versions", "default_terrain_key")
