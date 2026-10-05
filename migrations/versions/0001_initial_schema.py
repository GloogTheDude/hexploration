"""Create the historical Hexploration baseline schema.

Revision ID: 0001_initial_schema
Revises: None
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


_CAMPAIGN_ROLE = postgresql.ENUM("PLAYER", "DM", name="campaign_role", create_type=False)
_CHARACTER_STATUS = postgresql.ENUM(
    "ACTIVE", "RETIRED", "DEAD", name="character_status", create_type=False
)
_EXPEDITION_STATUS = postgresql.ENUM(
    "PLANNING", "ACTIVE", "DEBRIEFING", "RETURNED", "LOST", "DEAD", "ARCHIVED",
    name="expedition_status", create_type=False,
)


def upgrade() -> None:
    """Create only the schema that existed immediately before revision 0002."""
    bind = op.get_bind()
    for enum in (_CAMPAIGN_ROLE, _CHARACTER_STATUS, _EXPEDITION_STATUS):
        enum.create(bind, checkfirst=False)

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("epoch_name", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "campaign_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", _CAMPAIGN_ROLE, nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("campaign_id", "user_id", name="uq_campaign_membership"),
    )
    op.create_table(
        "characters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("race", sa.String(120), nullable=True),
        sa.Column("character_class", sa.String(120), nullable=True),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _CHARACTER_STATUS, nullable=False),
        sa.Column("current_game_minute", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("current_game_minute >= 0", name="ck_character_game_time_positive"),
    )
    op.create_table(
        "maps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "map_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("map_id", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=True),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("hex_size", sa.Integer(), nullable=False),
        sa.Column("effective_from_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["map_id"], ["maps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_version_id"], ["map_versions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("map_id", "version", name="uq_map_version"),
    )
    op.create_table(
        "map_hexes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("map_version_id", sa.Integer(), nullable=False),
        sa.Column("q", sa.Integer(), nullable=False),
        sa.Column("r", sa.Integer(), nullable=False),
        sa.Column("terrain_key", sa.String(80), nullable=False),
        sa.Column("elevation", sa.Integer(), nullable=False),
        sa.Column("travel_cost", sa.Float(), nullable=False),
        sa.Column("extra_data", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["map_version_id"], ["map_versions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("map_version_id", "q", "r", name="uq_map_hex_coordinate"),
    )
    op.create_table(
        "points_of_interest",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hex_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(80), nullable=True),
        sa.Column("dm_description", sa.Text(), nullable=True),
        sa.Column("is_landmark", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["hex_id"], ["map_hexes.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "expeditions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("status", _EXPEDITION_STATUS, nullable=False),
        sa.Column("start_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("current_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("return_game_minute", sa.BigInteger(), nullable=True),
        sa.Column("current_map_version_id", sa.Integer(), nullable=True),
        sa.Column("current_q", sa.Integer(), nullable=True),
        sa.Column("current_r", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_map_version_id"], ["map_versions.id"], ondelete="SET NULL"),
        sa.CheckConstraint("start_game_minute >= 0", name="ck_expedition_start_positive"),
        sa.CheckConstraint("current_game_minute >= start_game_minute", name="ck_expedition_current_after_start"),
    )
    op.create_table(
        "expedition_characters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expedition_id", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("joined_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("left_game_minute", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("expedition_id", "character_id", name="uq_expedition_character"),
    )
    op.create_table(
        "movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expedition_id", sa.Integer(), nullable=False),
        sa.Column("map_version_id", sa.Integer(), nullable=False),
        sa.Column("from_q", sa.Integer(), nullable=False),
        sa.Column("from_r", sa.Integer(), nullable=False),
        sa.Column("to_q", sa.Integer(), nullable=False),
        sa.Column("to_r", sa.Integer(), nullable=False),
        sa.Column("departure_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("arrival_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("base_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("effective_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("modifiers", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["map_version_id"], ["map_versions.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("arrival_game_minute >= departure_game_minute", name="ck_movement_time_order"),
    )
    op.create_table(
        "world_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("expedition_id", sa.Integer(), nullable=True),
        sa.Column("game_minute", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("dm_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "debrief_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "debrief_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["debrief_templates.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "expedition_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expedition_id", sa.Integer(), nullable=False),
        sa.Column("published_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "character_sheet_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("campaign_game_minute", sa.BigInteger(), nullable=True),
        sa.Column("expedition_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("character_id", "version", name="uq_character_sheet_version"),
    )
    op.create_table(
        "debrief_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expedition_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["debrief_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("expedition_id", "question_id", "character_id", name="uq_debrief_answer"),
    )
    op.create_table(
        "wiki_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("campaign_id", "slug", name="uq_wiki_campaign_slug"),
    )
    op.create_table(
        "wiki_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("effective_from_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("source_report_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["wiki_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_report_id"], ["expedition_reports.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("page_id", "revision", name="uq_wiki_revision"),
    )
    op.create_table(
        "knowledge_recalls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("expedition_id", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("knowledge_cutoff_game_minute", sa.BigInteger(), nullable=False),
        sa.Column("recalled_at_game_minute", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["expedition_id"], ["expeditions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["wiki_pages.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("expedition_id", "character_id", "page_id", name="uq_knowledge_recall_page"),
    )

    indexes = {
        "users": (("username", True), ("email", True)),
        "campaign_memberships": (("campaign_id", False), ("user_id", False)),
        "characters": (("campaign_id", False), ("owner_user_id", False)),
        "maps": (("campaign_id", False),),
        "map_versions": (("map_id", False), ("effective_from_game_minute", False)),
        "map_hexes": (("map_version_id", False),),
        "points_of_interest": (("hex_id", False),),
        "expeditions": (("campaign_id", False), ("return_game_minute", False)),
        "expedition_characters": (("expedition_id", False), ("character_id", False)),
        "movements": (("expedition_id", False), ("map_version_id", False), ("departure_game_minute", False), ("arrival_game_minute", False)),
        "world_events": (("campaign_id", False), ("expedition_id", False), ("game_minute", False), ("event_type", False)),
        "debrief_templates": (("campaign_id", False),),
        "debrief_questions": (("template_id", False),),
        "debrief_answers": (("expedition_id", False), ("character_id", False)),
        "expedition_reports": (("published_game_minute", False),),
        "character_sheet_versions": (("character_id", False), ("expedition_id", False)),
        "wiki_pages": (("campaign_id", False),),
        "wiki_revisions": (("page_id", False), ("effective_from_game_minute", False)),
        "knowledge_recalls": (("expedition_id", False), ("character_id", False), ("page_id", False)),
    }
    for table, columns in indexes.items():
        for column, unique in columns:
            op.create_index(f"ix_{table}_{column}", table, [column], unique=unique)
    op.create_index("ix_expedition_reports_expedition_id", "expedition_reports", ["expedition_id"], unique=True)


def downgrade() -> None:
    """Drop only the historical baseline, after later revisions are reversed."""
    for table in (
        "knowledge_recalls", "wiki_revisions", "wiki_pages", "debrief_answers",
        "character_sheet_versions", "expedition_reports", "world_events", "movements",
        "expedition_characters", "points_of_interest", "expeditions", "map_hexes",
        "map_versions", "maps", "debrief_questions", "debrief_templates", "characters",
        "campaign_memberships", "users", "campaigns",
    ):
        op.drop_table(table)

    bind = op.get_bind()
    for enum in (_EXPEDITION_STATUS, _CHARACTER_STATUS, _CAMPAIGN_ROLE):
        enum.drop(bind, checkfirst=False)
