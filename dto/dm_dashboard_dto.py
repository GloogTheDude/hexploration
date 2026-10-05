from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Any

from db.models import CampaignRole, CharacterStatus, ExpeditionStatus




class DMCampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    epoch_name: str | None = Field(default=None, min_length=1, max_length=80)


class DMMemberSummary(BaseModel):
    user_id: int
    username: str
    email: str
    role: CampaignRole


class DMMemberAdd(BaseModel):
    user_id: int
    role: CampaignRole = CampaignRole.PLAYER


class DMCharacterCreate(BaseModel):
    owner_user_id: int
    name: str = Field(min_length=1, max_length=120)
    race: str | None = Field(default=None, max_length=120)
    character_class: str | None = Field(default=None, max_length=120)
    level: int | None = Field(default=None, ge=1)
    description: str | None = None
    current_game_minute: int = Field(default=0, ge=0)


class DMEditorMapVersionCreate(BaseModel):
    parent_version_id: int = Field(gt=0)
    version_name: str | None = Field(default=None, max_length=160)
    effective_from_game_minute: int = Field(ge=0)


class DMEditorMapVersionUpdate(BaseModel):
    map_name: str | None = Field(default=None, min_length=1, max_length=160)
    version_name: str | None = Field(default=None, max_length=160)
    effective_from_game_minute: int = Field(ge=0)


class DMEditorLoadResponse(BaseModel):
    map_id: int
    map_version_id: int
    version: int
    hex_count: int


class DMEditorMapCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    version_name: str | None = Field(default="Initial version", max_length=160)
    effective_from_game_minute: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain non-whitespace characters")
        return value


class DMCampaignSummary(BaseModel):
    id: int
    name: str
    description: str | None
    epoch_name: str
    role: CampaignRole


class DMCharacterSummary(BaseModel):
    id: int
    owner_user_id: int
    owner_username: str = ""
    owner_role: CampaignRole | None = None
    name: str
    race: str | None
    character_class: str | None
    level: int | None
    status: CharacterStatus
    current_game_minute: int
    current_hp: int | None = None
    max_hp: int | None = None
    armor_class: int | None = None
    passive_perception: int | None = None
    sheet_version: int | None = None
    sheet_data: dict | None = None


class DMExpeditionParticipantSummary(BaseModel):
    character_id: int
    character_name: str
    joined_game_minute: int
    left_game_minute: int | None


class DMExpeditionSummary(BaseModel):
    id: int
    name: str
    status: ExpeditionStatus
    start_game_minute: int
    current_game_minute: int
    return_game_minute: int | None
    current_map_version_id: int | None
    current_q: int | None
    current_r: int | None
    weather_key: str | None
    transport_key: str | None
    ping_q: int | None = None
    ping_r: int | None = None
    ping_game_minute: int | None = None
    participants: list[DMExpeditionParticipantSummary]


class DMMapVersionSummary(BaseModel):
    id: int
    version: int
    name: str | None
    width: int
    height: int
    hex_size: int
    effective_from_game_minute: int
    hex_count: int
    poi_count: int
    edge_count: int
    hub_poi_id: int | None = None
    hub_name: str | None = None
    hub_q: int | None = None
    hub_r: int | None = None


class DMMapSummary(BaseModel):
    id: int
    name: str
    description: str | None
    versions: list[DMMapVersionSummary]


class DMWorldEventSummary(BaseModel):
    id: int
    game_minute: int
    event_type: str
    expedition_id: int | None
    target_type: str | None
    target_id: int | None
    payload: dict
    dm_note: str | None


class DMDashboardResponse(BaseModel):
    campaign: DMCampaignSummary
    campaign_game_minute: int
    active_expedition_count: int
    character_count: int
    map_count: int
    members: list[DMMemberSummary]
    characters: list[DMCharacterSummary]
    expeditions: list[DMExpeditionSummary]
    maps: list[DMMapSummary]
    recent_events: list[DMWorldEventSummary]

class DMExpeditionPlanCreate(BaseModel):
    name: str
    start_game_minute: int
    character_ids: list[int]
    map_version_id: int
    start_now: bool = False


class DMExpeditionPlanResponse(BaseModel):
    expedition_id: int
    status: ExpeditionStatus
    start_game_minute: int
    current_game_minute: int
    map_version_id: int
    q: int
    r: int
    transport_key: str | None
    participant_ids: list[int]

from typing import Any


class DMMapHexWorkbench(BaseModel):
    id: int
    q: int
    r: int
    terrain_key: str
    elevation: int
    visibility_score: int
    travel_cost: float
    extra_data: dict[str, Any]


class DMPOIWorkbench(BaseModel):
    id: int
    feature_id: int
    hex_id: int
    q: int
    r: int
    name: str
    kind: str | None
    dm_description: str | None
    player_description: str | None = None
    requires_discovery: bool = False
    is_landmark: bool
    is_hub: bool = False


class DMEdgeWorkbench(BaseModel):
    id: int
    from_q: int
    from_r: int
    to_q: int
    to_r: int
    feature_type: str
    feature_id: int
    segment_index: int = 0
    name: str | None
    extra_data: dict[str, Any]


class DMAreaWorkbench(BaseModel):
    id: int
    feature_type: str
    feature_id: int
    name: str | None
    cells: list[dict[str, int]]
    extra_data: dict[str, Any]


class DMMapWorkbenchResponse(BaseModel):
    campaign_id: int
    map_id: int
    map_name: str
    map_version_id: int
    version: int
    version_name: str | None
    effective_from_game_minute: int
    width: int
    height: int
    hex_size: int
    default_terrain_key: str | None = None
    hexes: list[DMMapHexWorkbench]
    pois: list[DMPOIWorkbench]
    edges: list[DMEdgeWorkbench]
    areas: list[DMAreaWorkbench] = Field(default_factory=list)


class DMPOICreate(BaseModel):
    q: int
    r: int
    feature_id: int | None = Field(default=None, gt=0)
    creation_game_minute: int = Field(default=0, ge=0)
    name: str = Field(min_length=1, max_length=160)
    kind: str | None = Field(default=None, max_length=80)
    dm_description: str | None = None
    player_description: str | None = None
    requires_discovery: bool = False
    is_landmark: bool = False
    is_hub: bool = False


class DMPOIUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    kind: str | None = Field(default=None, max_length=80)
    dm_description: str | None = None
    player_description: str | None = None
    requires_discovery: bool = False
    is_landmark: bool | None = None
    is_hub: bool | None = None


class DMFeatureEdgeCreate(BaseModel):
    from_q: int
    from_r: int
    to_q: int
    to_r: int
    feature_type: str = Field(min_length=1, max_length=80)
    name: str | None = Field(default=None, max_length=160)
    extra_data: dict[str, Any] = Field(default_factory=dict)


class DMTargetWorldEventCreate(BaseModel):
    game_minute: int = Field(ge=0)
    event_type: str = Field(min_length=1, max_length=120)
    expedition_id: int | None = Field(default=None, gt=0)
    payload: dict[str, Any] = Field(default_factory=dict)
    dm_note: str | None = None


class DMHexCoord(BaseModel):
    q: int
    r: int


class DMLinearFeatureCreate(BaseModel):
    waypoints: list[DMHexCoord] = Field(min_length=2)
    feature_type: str = Field(min_length=1, max_length=80)
    name: str | None = Field(default=None, max_length=160)
    extra_data: dict[str, Any] = Field(default_factory=dict)




class DMWorldEditorSnapshot(BaseModel):
    map_version_id: int
    features: list[dict[str, Any]] = Field(default_factory=list)
    pois: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    areas: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)


class DMHexFeatureClear(BaseModel):
    q: int
    r: int


class DMLinearFeatureUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=160)


class DMAreaFeatureUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=160)


class DMLinearFeatureMerge(BaseModel):
    edge_ids: list[int] = Field(min_length=2)


class DMAreaFeatureCreate(BaseModel):
    cells: list[DMHexCoord] = Field(min_length=1)
    feature_type: str = Field(min_length=1, max_length=80)
    name: str | None = Field(default=None, max_length=160)
    extra_data: dict[str, Any] = Field(default_factory=dict)
