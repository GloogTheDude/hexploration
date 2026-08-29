from __future__ import annotations

from pydantic import BaseModel


class PlayerMapHexResponse(BaseModel):
    q: int
    r: int
    discovery_state: str
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
    hexes: list[PlayerMapHexResponse]
    pois: list[PlayerMapPOIResponse]


class PlayerMapBootstrapResponse(BaseModel):
    expedition_id: int
    initialized: bool
    map_observations_created: int
    poi_observations_created: int
