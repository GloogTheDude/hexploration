from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from db.models import ExpeditionStatus


class ExpeditionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    start_game_minute: int = Field(default=0, ge=0)


class ExpeditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    name: str
    status: ExpeditionStatus
    start_game_minute: int
    current_game_minute: int
    return_game_minute: int | None
    current_map_version_id: int | None
    current_q: int | None
    current_r: int | None
    ping_q: int | None = None
    ping_r: int | None = None
    ping_game_minute: int | None = None
    created_at: datetime


class ExpeditionCharacterAdd(BaseModel):
    character_id: int = Field(gt=0)


class ExpeditionCharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    expedition_id: int
    character_id: int
    joined_game_minute: int
    left_game_minute: int | None
