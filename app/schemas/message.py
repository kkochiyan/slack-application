from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

class MessageUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

class MessageResponse(BaseModel):
    id: UUID
    channel_id: UUID
    author_id: UUID
    author_display_name: str | None = None
    content: str
    message_type: str
    edited_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True