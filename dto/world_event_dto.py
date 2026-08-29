from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorldEventCreate(BaseModel):
    game_minute: int = Field(ge=0)
    event_type: str = Field(min_length=1, max_length=120)
    expedition_id: int | None = None
    target_type: str | None = Field(default=None, max_length=80)
    target_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    dm_note: str | None = None


class WorldEventUpdate(BaseModel):
    game_minute: int | None = Field(default=None, ge=0)
    event_type: str | None = Field(default=None, min_length=1, max_length=120)
    expedition_id: int | None = None
    target_type: str | None = Field(default=None, max_length=80)
    target_id: int | None = None
    payload: dict[str, Any] | None = None
    dm_note: str | None = None


class WorldEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    expedition_id: int | None
    game_minute: int
    event_type: str
    target_type: str | None
    target_id: int | None
    payload: dict[str, Any]
    dm_note: str | None


class WorldStateResponse(BaseModel):
    campaign_id: int
    game_minute: int
    weather_key: str | None
    latest_global_events: list[WorldEventResponse]
    latest_target_events: list[WorldEventResponse]
