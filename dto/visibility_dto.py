from pydantic import BaseModel

from dto.knowledge_dto import KnowledgeObservationResponse
from dto.map_knowledge_dto import MapHexKnowledgeResponse


class VisiblePOIResponse(BaseModel):
    poi_id: int
    name: str
    kind: str | None
    q: int
    r: int
    distance: int
    max_visible_distance: int
    is_landmark: bool
    state: str
    exists: bool
    world_event_id: int | None
    weather_penalty: int
    landmark_bonus: int
    elevation_bonus: int
    terrain_concealment_penalty: int
    los_path: list[tuple[int, int]]


class OccludedPOIResponse(BaseModel):
    poi_id: int
    name: str
    kind: str | None
    q: int
    r: int
    distance: int
    max_visible_distance: int
    blocker_q: int
    blocker_r: int
    blocker_reason: str
    blocker_elevation: float | None
    sightline_elevation: float | None
    los_path: list[tuple[int, int]]


class VisibleHexResponse(BaseModel):
    q: int
    r: int
    terrain_key: str
    elevation: int
    visibility_score: int
    distance: int
    max_visible_distance: int
    weather_penalty: int
    elevation_bonus: int
    terrain_concealment_penalty: int
    los_path: list[tuple[int, int]]


class OccludedHexResponse(BaseModel):
    q: int
    r: int
    terrain_key: str
    elevation: int
    visibility_score: int
    distance: int
    max_visible_distance: int
    blocker_q: int
    blocker_r: int
    blocker_reason: str
    blocker_elevation: float | None
    sightline_elevation: float | None
    los_path: list[tuple[int, int]]


class ExpeditionVisibilityResponse(BaseModel):
    expedition_id: int
    game_minute: int
    map_version_id: int
    origin_q: int
    origin_r: int
    origin_visibility_score: int
    weather_key: str | None
    visible_hexes: list[VisibleHexResponse]
    occluded_hexes: list[OccludedHexResponse]
    visible_pois: list[VisiblePOIResponse]
    occluded_pois: list[OccludedPOIResponse]


class ExpeditionVisibilityObservationResponse(ExpeditionVisibilityResponse):
    observations: list[KnowledgeObservationResponse]
    map_observations: list[MapHexKnowledgeResponse]
