from pydantic import BaseModel, ConfigDict


class MapHexKnowledgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    expedition_id: int | None
    map_id: int
    map_version_id: int
    q: int
    r: int
    observed_game_minute: int
    discovery_state: str
    terrain_key: str
    elevation: int
    visibility_score: int
    extra_data: dict


class CharacterMapKnowledgeResponse(BaseModel):
    character_id: int
    map_id: int
    as_of_game_minute: int | None
    hexes: list[MapHexKnowledgeResponse]


class ExpeditionMapKnowledgeHexResponse(BaseModel):
    q: int
    r: int
    discovery_state: str
    terrain_key: str
    elevation: int
    visibility_score: int
    extra_data: dict
    observed_game_minute: int
    observed_by_character_id: int
    map_version_id: int


class ExpeditionMapKnowledgeResponse(BaseModel):
    expedition_id: int
    map_id: int
    as_of_game_minute: int
    hexes: list[ExpeditionMapKnowledgeHexResponse]
