from uuid import UUID

from pydantic import BaseModel, EmailStr

class ChannelMemberAdd(BaseModel):
    user_id: UUID

class ChannelMemberResponse(BaseModel):
    id: UUID
    channel_id: UUID
    user_id: UUID
    role: str

    class Config:
        from_attributes = True