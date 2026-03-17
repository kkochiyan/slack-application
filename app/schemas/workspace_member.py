from uuid import UUID

from pydantic import BaseModel

class WorkspaceMemberAdd(BaseModel):
    user_id: UUID

class WorkspaceMemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str

    class Config:
        from_attributes = True

