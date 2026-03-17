from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)

async def get_cuurent_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
        db: AsyncSession = Depends(get_db)
):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return await AuthService.get_current_user(db, credentials.credentials)