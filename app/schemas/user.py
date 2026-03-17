from uuid import UUID

from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str

    class Config:
        from_attributes = True