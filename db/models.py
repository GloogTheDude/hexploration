from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class CampaignRole(str, Enum):
    PLAYER = "PLAYER"
    DM = "DM"


class CharacterStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    DEAD = "DEAD"


class ExpeditionStatus(str, Enum):
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    DEBRIEFING = "DEBRIEFING"
    RETURNED = "RETURNED"
    LOST = "LOST"
    DEAD = "DEAD"
    ARCHIVED = "ARCHIVED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    memberships: Mapped[list[CampaignMembership]] = relationship(back_populates="user")
    characters: Mapped[list[Character]] = relationship(back_populates="owner")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text())
    epoch_name: Mapped[str] = mapped_column(String(80), default="Day 1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    memberships: Mapped[list[CampaignMembership]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    characters: Mapped[list[Character]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    maps: Mapped[list[WorldMap]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    expeditions: Mapped[list[Expedition]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class CampaignMembership(Base):
    __tablename__ = "campaign_memberships"
    __table_args__ = (UniqueConstraint("campaign_id", "user_id", name="uq_campaign_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[CampaignRole] = mapped_column(SAEnum(CampaignRole, name="campaign_role"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    campaign: Mapped[Campaign] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (CheckConstraint("current_game_minute >= 0", name="ck_character_game_time_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    race: Mapped[str | None] = mapped_column(String(120))
    character_class: Mapped[str | None] = mapped_column(String(120))
    level: Mapped[int | None] = mapped_column(Integer())
    description: Mapped[str | None] = mapped_column(Text())
    status: Mapped[CharacterStatus] = mapped_column(SAEnum(CharacterStatus, name="character_status"), default=CharacterStatus.ACTIVE)
    current_game_minute: Mapped[int] = mapped_column(BigInteger(), default=0)

    campaign: Mapped[Campaign] = relationship(back_populates="characters")
    owner: Mapped[User] = relationship(back_populates="characters")
    sheets: Mapped[list[CharacterSheetVersion]] = relationship(back_populates="character", cascade="all, delete-orphan")


class CharacterSheetVersion(Base):
    __tablename__ = "character_sheet_versions"
    __table_args__ = (UniqueConstraint("character_id", "version", name="uq_character_sheet_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer())
    storage_key: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf")
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    campaign_game_minute: Mapped[int | None] = mapped_column(BigInteger())
    expedition_id: Mapped[int | None] = mapped_column(ForeignKey("expeditions.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    is_current: Mapped[bool] = mapped_column(Boolean(), default=True)

    character: Mapped[Character] = relationship(back_populates="sheets")


class WorldMap(Base):
    __tablename__ = "maps"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    campaign: Mapped[Campaign] = relationship(back_populates="maps")
    versions: Mapped[list[MapVersion]] = relationship(back_populates="map", cascade="all, delete-orphan")


class MapVersion(Base):
    __tablename__ = "map_versions"
    __table_args__ = (UniqueConstraint("map_id", "version", name="uq_map_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    map_id: Mapped[int] = mapped_column(ForeignKey("maps.id", ondelete="CASCADE"), index=True)
    parent_version_id: Mapped[int | None] = mapped_column(ForeignKey("map_versions.id", ondelete="SET NULL"))
    version: Mapped[int] = mapped_column(Integer())
    name: Mapped[str | None] = mapped_column(String(160))
    width: Mapped[int] = mapped_column(Integer())
    height: Mapped[int] = mapped_column(Integer())
    hex_size: Mapped[int] = mapped_column(Integer(), default=32)
    effective_from_game_minute: Mapped[int] = mapped_column(BigInteger(), default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    map: Mapped[WorldMap] = relationship(back_populates="versions")
    hexes: Mapped[list[MapHex]] = relationship(back_populates="map_version", cascade="all, delete-orphan")


class MapHex(Base):
    __tablename__ = "map_hexes"
    __table_args__ = (UniqueConstraint("map_version_id", "q", "r", name="uq_map_hex_coordinate"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    map_version_id: Mapped[int] = mapped_column(ForeignKey("map_versions.id", ondelete="CASCADE"), index=True)
    q: Mapped[int] = mapped_column(Integer())
    r: Mapped[int] = mapped_column(Integer())
    terrain_key: Mapped[str] = mapped_column(String(80), default="SEA")
    elevation: Mapped[int] = mapped_column(Integer(), default=0)
    travel_cost: Mapped[float] = mapped_column(Float(), default=1.0)
    extra_data: Mapped[dict] = mapped_column(JSON(), default=dict)

    map_version: Mapped[MapVersion] = relationship(back_populates="hexes")
    pois: Mapped[list[PointOfInterest]] = relationship(back_populates="hex", cascade="all, delete-orphan")


class PointOfInterest(Base):
    __tablename__ = "points_of_interest"

    id: Mapped[int] = mapped_column(primary_key=True)
    hex_id: Mapped[int] = mapped_column(ForeignKey("map_hexes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str | None] = mapped_column(String(80))
    dm_description: Mapped[str | None] = mapped_column(Text())
    is_landmark: Mapped[bool] = mapped_column(Boolean(), default=False)

    hex: Mapped[MapHex] = relationship(back_populates="pois")


class Expedition(Base):
    __tablename__ = "expeditions"
    __table_args__ = (
        CheckConstraint("start_game_minute >= 0", name="ck_expedition_start_positive"),
        CheckConstraint("current_game_minute >= start_game_minute", name="ck_expedition_current_after_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    status: Mapped[ExpeditionStatus] = mapped_column(SAEnum(ExpeditionStatus, name="expedition_status"), default=ExpeditionStatus.PLANNING)
    start_game_minute: Mapped[int] = mapped_column(BigInteger())
    current_game_minute: Mapped[int] = mapped_column(BigInteger())
    return_game_minute: Mapped[int | None] = mapped_column(BigInteger(), index=True)
    current_map_version_id: Mapped[int | None] = mapped_column(ForeignKey("map_versions.id", ondelete="SET NULL"))
    current_q: Mapped[int | None] = mapped_column(Integer())
    current_r: Mapped[int | None] = mapped_column(Integer())
    weather_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    transport_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    campaign: Mapped[Campaign] = relationship(back_populates="expeditions")
    participants: Mapped[list[ExpeditionCharacter]] = relationship(back_populates="expedition", cascade="all, delete-orphan")
    movements: Mapped[list[Movement]] = relationship(back_populates="expedition", cascade="all, delete-orphan")


class ExpeditionCharacter(Base):
    __tablename__ = "expedition_characters"
    __table_args__ = (UniqueConstraint("expedition_id", "character_id", name="uq_expedition_character"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expedition_id: Mapped[int] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    joined_game_minute: Mapped[int] = mapped_column(BigInteger())
    left_game_minute: Mapped[int | None] = mapped_column(BigInteger())

    expedition: Mapped[Expedition] = relationship(back_populates="participants")
    character: Mapped[Character] = relationship()


class Movement(Base):
    __tablename__ = "movements"
    __table_args__ = (CheckConstraint("arrival_game_minute >= departure_game_minute", name="ck_movement_time_order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expedition_id: Mapped[int] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"), index=True)
    map_version_id: Mapped[int] = mapped_column(ForeignKey("map_versions.id", ondelete="RESTRICT"), index=True)
    from_q: Mapped[int] = mapped_column(Integer())
    from_r: Mapped[int] = mapped_column(Integer())
    to_q: Mapped[int] = mapped_column(Integer())
    to_r: Mapped[int] = mapped_column(Integer())
    departure_game_minute: Mapped[int] = mapped_column(BigInteger(), index=True)
    arrival_game_minute: Mapped[int] = mapped_column(BigInteger(), index=True)
    base_duration_minutes: Mapped[int] = mapped_column(Integer())
    effective_duration_minutes: Mapped[int] = mapped_column(Integer())
    modifiers: Mapped[list] = mapped_column(JSON(), default=list)

    expedition: Mapped[Expedition] = relationship(back_populates="movements")


class WorldEvent(Base):
    __tablename__ = "world_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    expedition_id: Mapped[int | None] = mapped_column(ForeignKey("expeditions.id", ondelete="SET NULL"), index=True)
    game_minute: Mapped[int] = mapped_column(BigInteger(), index=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    target_type: Mapped[str | None] = mapped_column(String(80))
    target_id: Mapped[int | None] = mapped_column(Integer())
    payload: Mapped[dict] = mapped_column(JSON(), default=dict)
    dm_note: Mapped[str | None] = mapped_column(Text())


class DebriefTemplate(Base):
    __tablename__ = "debrief_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)


class DebriefQuestion(Base):
    __tablename__ = "debrief_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("debrief_templates.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer())
    prompt: Mapped[str] = mapped_column(Text())


class DebriefAnswer(Base):
    __tablename__ = "debrief_answers"
    __table_args__ = (UniqueConstraint("expedition_id", "question_id", "character_id", name="uq_debrief_answer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expedition_id: Mapped[int] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("debrief_questions.id", ondelete="CASCADE"))
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    answer: Mapped[str] = mapped_column(Text())
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExpeditionReport(Base):
    __tablename__ = "expedition_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    expedition_id: Mapped[int] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"), unique=True, index=True)
    published_game_minute: Mapped[int] = mapped_column(BigInteger(), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class WikiPage(Base):
    __tablename__ = "wiki_pages"
    __table_args__ = (UniqueConstraint("campaign_id", "slug", name="uq_wiki_campaign_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(180))
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(100))


class WikiRevision(Base):
    __tablename__ = "wiki_revisions"
    __table_args__ = (UniqueConstraint("page_id", "revision", name="uq_wiki_revision"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("wiki_pages.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer())
    effective_from_game_minute: Mapped[int] = mapped_column(BigInteger(), index=True)
    source_report_id: Mapped[int | None] = mapped_column(ForeignKey("expedition_reports.id", ondelete="SET NULL"))
    content: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class KnowledgeRecall(Base):
    __tablename__ = "knowledge_recalls"
    __table_args__ = (UniqueConstraint("expedition_id", "character_id", "page_id", name="uq_knowledge_recall_page"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expedition_id: Mapped[int] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("wiki_pages.id", ondelete="CASCADE"), index=True)
    knowledge_cutoff_game_minute: Mapped[int] = mapped_column(BigInteger())
    recalled_at_game_minute: Mapped[int] = mapped_column(BigInteger())
