from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from db.models import CampaignRole


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    epoch_name: str = Field(default="Day 1", min_length=1, max_length=80)
    creator_user_id: int


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    epoch_name: str
    created_at: datetime


class MembershipCreate(BaseModel):
    user_id: int
    role: CampaignRole = CampaignRole.PLAYER


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    user_id: int
    role: CampaignRole
    joined_at: datetime
