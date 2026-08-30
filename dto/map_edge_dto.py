from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MapEdgeCreate(BaseModel):
    from_q: int
    from_r: int
    to_q: int
    to_r: int
    feature_type: str = Field(min_length=1, max_length=80)
    feature_id: int = Field(gt=0)
    segment_index: int = Field(default=0, ge=0)
    name: str | None = Field(default=None, max_length=160)
    extra_data: dict[str, Any] = Field(default_factory=dict)


class MapEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    map_version_id: int
    from_q: int
    from_r: int
    to_q: int
    to_r: int
    feature_type: str
    feature_id: int
    segment_index: int = 0
    name: str | None
    extra_data: dict[str, Any]
