from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field

class POICreate(BaseModel):
    hex_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=160)
    kind: str | None = Field(default=None, max_length=80)
    dm_description: str | None = None
    is_landmark: bool = False

class POIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    feature_id: int
    hex_id: int
    name: str
    kind: str | None
    dm_description: str | None
    is_landmark: bool

class POITemporalStateResponse(BaseModel):
    poi: POIResponse
    game_minute: int
    state: str
    exists: bool
    visible_at_distance: bool
    latest_event: dict | None = None
