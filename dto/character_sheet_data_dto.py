from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CharacterSheetForm(BaseModel):
    """Editable, DB-backed subset of the classic D&D 5e character sheet.

    The application owns these values. The official fillable PDF is only an
    export target and is never the source of truth.
    """

    character_name: str = Field(default="", max_length=120)
    player_name: str = Field(default="", max_length=120)
    race: str = Field(default="", max_length=120)
    character_class: str = Field(default="", max_length=120)
    level: int | None = Field(default=1, ge=1, le=20)
    background: str = Field(default="", max_length=160)
    alignment: str = Field(default="", max_length=80)
    experience_points: int | None = Field(default=None, ge=0)

    strength: int = Field(default=10, ge=1, le=30)
    dexterity: int = Field(default=10, ge=1, le=30)
    constitution: int = Field(default=10, ge=1, le=30)
    intelligence: int = Field(default=10, ge=1, le=30)
    wisdom: int = Field(default=10, ge=1, le=30)
    charisma: int = Field(default=10, ge=1, le=30)

    armor_class: int | None = Field(default=None, ge=0, le=99)
    initiative: int | None = Field(default=None, ge=-20, le=30)
    speed: str = Field(default="", max_length=40)
    proficiency_bonus: int | None = Field(default=None, ge=0, le=20)
    max_hp: int | None = Field(default=None, ge=0, le=9999)
    current_hp: int | None = Field(default=None, ge=-999, le=9999)
    temp_hp: int | None = Field(default=None, ge=0, le=9999)
    hit_dice_total: str = Field(default="", max_length=40)
    hit_dice_current: str = Field(default="", max_length=40)
    passive_perception: int | None = Field(default=None, ge=0, le=99)

    personality_traits: str = Field(default="", max_length=4000)
    ideals: str = Field(default="", max_length=4000)
    bonds: str = Field(default="", max_length=4000)
    flaws: str = Field(default="", max_length=4000)
    attacks_spellcasting: str = Field(default="", max_length=8000)
    equipment: str = Field(default="", max_length=8000)
    proficiencies_languages: str = Field(default="", max_length=8000)
    features_traits: str = Field(default="", max_length=12000)

    age: str = Field(default="", max_length=40)
    height: str = Field(default="", max_length=40)
    weight: str = Field(default="", max_length=40)
    eyes: str = Field(default="", max_length=80)
    skin: str = Field(default="", max_length=80)
    hair: str = Field(default="", max_length=80)
    appearance: str = Field(default="", max_length=8000)
    allies_organizations: str = Field(default="", max_length=8000)
    backstory: str = Field(default="", max_length=16000)
    additional_features_traits: str = Field(default="", max_length=12000)
    treasure: str = Field(default="", max_length=8000)
    notes: str = Field(default="", max_length=16000)


class CharacterSheetDataVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_id: int
    version: int
    data: dict
    campaign_game_minute: int
    created_at: datetime
    is_current: bool
