from __future__ import annotations

from datetime import UTC, datetime
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
    ping_color: Mapped[str] = mapped_column(String(7), default="#ff4f64")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    memberships: Mapped[list[CampaignMembership]] = relationship(back_populates="user")
    received_campaign_invitations: Mapped[list[CampaignInvitation]] = relationship(foreign_keys="CampaignInvitation.invited_user_id", back_populates="invited_user")
    sent_campaign_invitations: Mapped[list[CampaignInvitation]] = relationship(foreign_keys="CampaignInvitation.invited_by_user_id", back_populates="invited_by_user")
    characters: Mapped[list[Character]] = relationship(back_populates="owner")
    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_user_session_token_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text())
    epoch_name: Mapped[str] = mapped_column(String(80), default="Day 1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    memberships: Mapped[list[CampaignMembership]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    invitations: Mapped[list[CampaignInvitation]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
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
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    campaign: Mapped[Campaign] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class CampaignInvitation(Base):
    __tablename__ = "campaign_invitations"
    __table_args__ = (
        UniqueConstraint("campaign_id", "invited_user_id", name="uq_campaign_invitation_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    invited_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    invited_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    campaign: Mapped[Campaign] = relationship(back_populates="invitations")
    invited_user: Mapped[User] = relationship(foreign_keys=[invited_user_id], back_populates="received_campaign_invitations")
    invited_by_user: Mapped[User] = relationship(foreign_keys=[invited_by_user_id], back_populates="sent_campaign_invitations")


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
    sheet_data_versions: Mapped[list[CharacterSheetDataVersion]] = relationship(back_populates="character", cascade="all, delete-orphan")


class CharacterSheetDataVersion(Base):
    __tablename__ = "character_sheet_data_versions"
    __table_args__ = (UniqueConstraint("character_id", "version", name="uq_character_sheet_data_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer())
    data: Mapped[dict] = mapped_column(JSON())
    campaign_game_minute: Mapped[int] = mapped_column(BigInteger(), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_current: Mapped[bool] = mapped_column(Boolean(), default=True)

    character: Mapped[Character] = relationship(back_populates="sheet_data_versions")


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_current: Mapped[bool] = mapped_column(Boolean(), default=True)

    character: Mapped[Character] = relationship(back_populates="sheets")


class WorldMap(Base):
    __tablename__ = "maps"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    campaign: Mapped[Campaign] = relationship(back_populates="maps")
    versions: Mapped[list[MapVersion]] = relationship(back_populates="map", cascade="all, delete-orphan")
    features: Mapped[list[MapFeature]] = relationship(back_populates="map", cascade="all, delete-orphan")


class MapFeature(Base):
    """Campaign/map-scoped semantic identity shared by all MapVersions.

    ``feature_id`` is the stable integer used by WorldEvent.target_id. The
    concrete POI/edge rows may be recreated for each MapVersion, but this
    identity remains stable across those versions.
    """

    __tablename__ = "map_features"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "feature_type", "feature_id",
            name="uq_map_feature_campaign_type_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    map_id: Mapped[int] = mapped_column(
        ForeignKey("maps.id", ondelete="CASCADE"), index=True
    )
    feature_type: Mapped[str] = mapped_column(String(80), index=True)
    feature_id: Mapped[int] = mapped_column(Integer(), index=True)
    # Directed semantic link used by river networks. Tributaries keep their own
    # stable identity and terminate at the confluence instead of duplicating the
    # downstream geometry.
    downstream_feature_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    downstream_feature_id: Mapped[int | None] = mapped_column(Integer(), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    map: Mapped[WorldMap] = relationship(back_populates="features")


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
    # Non-null means sparse storage: absent MapHex rows inherit this terrain.
    # NULL keeps pre-v30 dense versions backward compatible.
    default_terrain_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    effective_from_game_minute: Mapped[int] = mapped_column(BigInteger(), default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    map: Mapped[WorldMap] = relationship(back_populates="versions")
    hexes: Mapped[list[MapHex]] = relationship(back_populates="map_version", cascade="all, delete-orphan")
    edges: Mapped[list[MapEdge]] = relationship(back_populates="map_version", cascade="all, delete-orphan")
    areas: Mapped[list[MapArea]] = relationship(back_populates="map_version", cascade="all, delete-orphan")


class MapHex(Base):
    __tablename__ = "map_hexes"
    __table_args__ = (UniqueConstraint("map_version_id", "q", "r", name="uq_map_hex_coordinate"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    map_version_id: Mapped[int] = mapped_column(ForeignKey("map_versions.id", ondelete="CASCADE"), index=True)
    q: Mapped[int] = mapped_column(Integer())
    r: Mapped[int] = mapped_column(Integer())
    terrain_key: Mapped[str] = mapped_column(String(80), default="SEA")
    elevation: Mapped[int] = mapped_column(Integer(), default=0)
    visibility_score: Mapped[int] = mapped_column(Integer(), default=3)
    travel_cost: Mapped[float] = mapped_column(Float(), default=1.0)
    extra_data: Mapped[dict] = mapped_column(JSON(), default=dict)

    map_version: Mapped[MapVersion] = relationship(back_populates="hexes")
    pois: Mapped[list[PointOfInterest]] = relationship(back_populates="hex", cascade="all, delete-orphan")




class MapEdge(Base):
    __tablename__ = "map_edges"
    __table_args__ = (
        UniqueConstraint(
            "map_version_id",
            "from_q",
            "from_r",
            "to_q",
            "to_r",
            "feature_type",
            "feature_id",
            name="uq_map_edge_feature_coordinates",
        ),
        CheckConstraint("feature_id > 0", name="ck_map_edge_feature_id_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    map_version_id: Mapped[int] = mapped_column(
        ForeignKey("map_versions.id", ondelete="CASCADE"),
        index=True,
    )
    from_q: Mapped[int] = mapped_column(Integer())
    from_r: Mapped[int] = mapped_column(Integer())
    to_q: Mapped[int] = mapped_column(Integer())
    to_r: Mapped[int] = mapped_column(Integer())
    feature_type: Mapped[str] = mapped_column(String(80), index=True)
    feature_id: Mapped[int] = mapped_column(Integer(), index=True)
    segment_index: Mapped[int] = mapped_column(Integer(), default=0)
    name: Mapped[str | None] = mapped_column(String(160))
    extra_data: Mapped[dict] = mapped_column(JSON(), default=dict)

    map_version: Mapped[MapVersion] = relationship(back_populates="edges")


class MapArea(Base):
    """Semantic area feature represented by an ordered set of map cells.

    The stable identity is (feature_type, feature_id); ``cells`` is only the
    concrete geometry for this MapVersion.
    """

    __tablename__ = "map_areas"
    __table_args__ = (
        UniqueConstraint("map_version_id", "feature_type", "feature_id", name="uq_map_area_feature"),
        CheckConstraint("feature_id > 0", name="ck_map_area_feature_id_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    map_version_id: Mapped[int] = mapped_column(ForeignKey("map_versions.id", ondelete="CASCADE"), index=True)
    feature_type: Mapped[str] = mapped_column(String(80), index=True)
    feature_id: Mapped[int] = mapped_column(Integer(), index=True)
    name: Mapped[str | None] = mapped_column(String(160))
    cells: Mapped[list] = mapped_column(JSON(), default=list)
    extra_data: Mapped[dict] = mapped_column(JSON(), default=dict)

    map_version: Mapped[MapVersion] = relationship(back_populates="areas")


class PointOfInterest(Base):
    __tablename__ = "points_of_interest"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature_id: Mapped[int] = mapped_column(Integer(), index=True)
    hex_id: Mapped[int] = mapped_column(ForeignKey("map_hexes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str | None] = mapped_column(String(80))
    dm_description: Mapped[str | None] = mapped_column(Text())
    player_description: Mapped[str | None] = mapped_column(Text())
    requires_discovery: Mapped[bool] = mapped_column(Boolean(), default=False)
    is_landmark: Mapped[bool] = mapped_column(Boolean(), default=False)
    is_hub: Mapped[bool] = mapped_column(Boolean(), default=False, index=True)

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
    ping_q: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    ping_r: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    ping_game_minute: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    ping_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    ping_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dm_ping_q: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    dm_ping_r: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    dm_ping_game_minute: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    dm_ping_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    dm_ping_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

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


class CharacterKnowledgeObservation(Base):
    __tablename__ = "character_knowledge_observations"
    __table_args__ = (
        UniqueConstraint(
            "character_id",
            "target_type",
            "target_id",
            "observed_game_minute",
            "expedition_id",
            name="uq_character_knowledge_observation",
        ),
        CheckConstraint(
            "observed_game_minute >= 0",
            name="ck_character_knowledge_observed_minute_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"),
        index=True,
    )
    expedition_id: Mapped[int | None] = mapped_column(
        ForeignKey("expeditions.id", ondelete="SET NULL"),
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(80), index=True)
    target_id: Mapped[int] = mapped_column(Integer(), index=True)
    observed_game_minute: Mapped[int] = mapped_column(BigInteger(), index=True)
    source_type: Mapped[str] = mapped_column(String(80), default="OBSERVATION")
    knowledge: Mapped[dict] = mapped_column(JSON(), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    character: Mapped[Character] = relationship()
    expedition: Mapped[Expedition | None] = relationship()


class CharacterMapHexObservation(Base):
    __tablename__ = "character_map_hex_observations"
    __table_args__ = (
        UniqueConstraint(
            "character_id",
            "map_id",
            "q",
            "r",
            "observed_game_minute",
            "expedition_id",
            name="uq_character_map_hex_observation",
        ),
        CheckConstraint(
            "observed_game_minute >= 0",
            name="ck_character_map_hex_observed_minute_positive",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"),
        index=True,
    )
    expedition_id: Mapped[int | None] = mapped_column(
        ForeignKey("expeditions.id", ondelete="SET NULL"),
        index=True,
    )
    map_id: Mapped[int] = mapped_column(
        ForeignKey("maps.id", ondelete="CASCADE"),
        index=True,
    )
    map_version_id: Mapped[int] = mapped_column(
        ForeignKey("map_versions.id", ondelete="RESTRICT"),
        index=True,
    )
    q: Mapped[int] = mapped_column(Integer(), index=True)
    r: Mapped[int] = mapped_column(Integer(), index=True)
    observed_game_minute: Mapped[int] = mapped_column(BigInteger(), index=True)
    discovery_state: Mapped[str] = mapped_column(String(20), default="SEEN")
    terrain_key: Mapped[str] = mapped_column(String(80))
    elevation: Mapped[int] = mapped_column(Integer())
    visibility_score: Mapped[int] = mapped_column(Integer())
    extra_data: Mapped[dict] = mapped_column(JSON(), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    character: Mapped[Character] = relationship()
    expedition: Mapped[Expedition | None] = relationship()
    map: Mapped[WorldMap] = relationship()
    map_version: Mapped[MapVersion] = relationship()


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
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExpeditionReport(Base):
    __tablename__ = "expedition_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    expedition_id: Mapped[int] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"), unique=True, index=True)
    published_game_minute: Mapped[int] = mapped_column(BigInteger(), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class KnowledgeRecall(Base):
    __tablename__ = "knowledge_recalls"
    __table_args__ = (UniqueConstraint("expedition_id", "character_id", "page_id", name="uq_knowledge_recall_page"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expedition_id: Mapped[int] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("wiki_pages.id", ondelete="CASCADE"), index=True)
    knowledge_cutoff_game_minute: Mapped[int] = mapped_column(BigInteger())
    recalled_at_game_minute: Mapped[int] = mapped_column(BigInteger())
