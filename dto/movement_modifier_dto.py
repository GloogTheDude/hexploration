from __future__ import annotations

from pydantic import BaseModel, Field


class MovementModifierInput(BaseModel):
    type: str = Field(min_length=1, max_length=40)
    key: str = Field(min_length=1, max_length=80)
    multiplier: float = Field(gt=0)


class MovementModifierSet(BaseModel):
    weather_key: str | None = Field(default=None, max_length=80)
    transport_key: str | None = Field(default=None, max_length=80)


class MovementModifierState(BaseModel):
    expedition_id: int
    weather_key: str | None
    transport_key: str | None
