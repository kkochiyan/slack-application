from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix='/auth', tags=["Auth"])

@router.post("/register", response_model=UserResponse)
async def register(
        data: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    user = await UserService.create_user(
        db,
        email=data.email,
        password=data.password,
        display_name=data.display_name
    )

    return user

@router.post("/login", response_model=TokenResponse)
async def login(
        data: LoginRequest,
        db: AsyncSession = Depends(get_db)
):
    return await AuthService.login(
        db,
        email=data.email,
        password=data.password
    )