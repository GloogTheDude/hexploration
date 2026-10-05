from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PlayerMapHexResponse(BaseModel):
    q: int
    r: int
    discovery_state: str
    visibility_state: str = "SEEN"
    terrain_key: str
    elevation: int
    visibility_score: int
    observed_game_minute: int
    map_version_id: int


class PlayerMapPOIResponse(BaseModel):
    poi_id: int
    name: str
    kind: str | None
    q: int
    r: int
    state: str | None
    exists: bool | None
    observed_game_minute: int
    description: str | None = None


class PlayerMapEdgeResponse(BaseModel):
    feature_type: str
    feature_id: int
    name: str | None = None
    from_q: int
    from_r: int
    to_q: int
    to_r: int


class PlayerMapAreaResponse(BaseModel):
    feature_type: str
    feature_id: int
    name: str | None = None
    cells: list[dict[str, int]]


class PlayerMapResponse(BaseModel):
    expedition_id: int
    expedition_name: str
    expedition_status: str
    current_game_minute: int
    map_id: int
    map_name: str
    map_version_id: int
    map_version: int
    hex_size: int
    current_q: int
    current_r: int
    weather_key: str | None
    transport_key: str | None
    ping_q: int | None = None
    ping_r: int | None = None
    ping_game_minute: int | None = None
    ping_user_id: int | None = None
    ping_username: str | None = None
    ping_color: str | None = None
    ping_created_at: datetime | None = None
    dm_ping_q: int | None = None
    dm_ping_r: int | None = None
    dm_ping_game_minute: int | None = None
    dm_ping_user_id: int | None = None
    dm_ping_username: str | None = None
    dm_ping_color: str | None = None
    dm_ping_created_at: datetime | None = None
    hexes: list[PlayerMapHexResponse]
    pois: list[PlayerMapPOIResponse]
    edges: list[PlayerMapEdgeResponse] = []
    areas: list[PlayerMapAreaResponse] = []


class PlayerMapBootstrapResponse(BaseModel):
    expedition_id: int
    initialized: bool
    map_observations_created: int
    poi_observations_created: int


class ExpeditionPingSet(BaseModel):
    q: int
    r: int


class ExpeditionPingResponse(BaseModel):
    expedition_id: int
    q: int | None
    r: int | None
    game_minute: int | None
    user_id: int | None = None
    username: str | None = None
    color: str | None = None
    created_at: datetime | None = None
