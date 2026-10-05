from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MapSnapshotResponse(BaseModel):
    map_id: int
    map_version_id: int
    version: int
    width: int
    height: int
    hex_size: int
    hex_count: int


class ExpeditionPositionSet(BaseModel):
    map_version_id: int = Field(gt=0)
    q: int
    r: int


class ExpeditionPositionResponse(BaseModel):
    expedition_id: int
    map_version_id: int
    q: int
    r: int
    current_game_minute: int


class ExpeditionMoveRequest(BaseModel):
    to_q: int
    to_r: int
    base_duration_minutes: int = Field(default=60, gt=0)


class MovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    expedition_id: int
    map_version_id: int
    from_q: int
    from_r: int
    to_q: int
    to_r: int
    departure_game_minute: int
    arrival_game_minute: int
    base_duration_minutes: int
    effective_duration_minutes: int
    modifiers: list


class MovementUndoResponse(BaseModel):
    movement: MovementResponse
    expedition_id: int
    current_q: int
    current_r: int
    current_game_minute: int
