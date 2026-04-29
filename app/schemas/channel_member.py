from uuid import UUID

from pydantic import BaseModel, EmailStr

class ChannelMemberAdd(BaseModel):
    email: EmailStr

class ChannelMemberResponse(BaseModel):
    id: UUID
    channel_id: UUID
    user_id: UUID
    display_name: str | None = None
    role: str

    class Config:
        from_attributes = True