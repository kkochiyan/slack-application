from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["Users"])

security = HTTPBearer()

@router.get("/me", response_model=UserResponse)
async def get_me(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
        )

    user = await AuthService.get_current_user(db, credentials.credentials)
    return user