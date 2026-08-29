from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgeObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    expedition_id: int | None
    target_type: str
    target_id: int
    observed_game_minute: int
    source_type: str
    knowledge: dict
    created_at: datetime


class POIDiscoveryResponse(BaseModel):
    expedition_id: int
    poi_id: int
    observed_game_minute: int
    observations: list[KnowledgeObservationResponse]


class CharacterKnowledgeSummary(BaseModel):
    character_id: int
    as_of_game_minute: int | None
    observations: list[KnowledgeObservationResponse]
