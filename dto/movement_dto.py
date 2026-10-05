from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MapSnapshotCreate(BaseModel):
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
