from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class UserPingColorUpdate(BaseModel):
    ping_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    ping_color: str = "#ff4f64"
    created_at: datetime
