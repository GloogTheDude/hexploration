from pydantic import BaseModel, ConfigDict, Field, field_validator

from db.models import CharacterStatus


class CharacterCreate(BaseModel):
    owner_user_id: int
    name: str = Field(min_length=1, max_length=120)
    race: str | None = Field(default=None, max_length=120)
    character_class: str | None = Field(default=None, max_length=120)
    level: int | None = Field(default=None, ge=1)
    description: str | None = None
    current_game_minute: int = Field(default=0, ge=0)

    @field_validator("name")
    @classmethod
    def reject_blank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must contain non-whitespace characters")
        return value


class CharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    owner_user_id: int
    name: str
    race: str | None
    character_class: str | None
    level: int | None
    description: str | None
    status: CharacterStatus
    current_game_minute: int
