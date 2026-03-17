from uuid import UUID

from pydantic import BaseModel, Field

class ChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    is_private: bool = False

class ChannelResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    is_private: bool
    created_by: UUID

    class Config:
        from_attributes = True