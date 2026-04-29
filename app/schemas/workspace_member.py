from uuid import UUID

from pydantic import BaseModel, EmailStr

class WorkspaceMemberAdd(BaseModel):
    email: EmailStr

class WorkspaceMemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str
    display_name: str | None

    class Config:
        from_attributes = True