from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class CampaignInvitationCreate(BaseModel):
    invited_user_id: int = Field(gt=0)

class CampaignInvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    campaign_id: int
    campaign_name: str
    invited_user_id: int
    invited_username: str
    invited_by_user_id: int
    invited_by_username: str
    status: str
    created_at: datetime
    responded_at: datetime | None
