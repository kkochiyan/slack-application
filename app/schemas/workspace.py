from uuid import UUID

from pydantic import BaseModel, Field

class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=3, max_length=255)

class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    owner_id: UUID

    class Config:
        from_attributes = True