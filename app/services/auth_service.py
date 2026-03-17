from fastapi import HTTPException, status
from jose import JWTError

from app.core.security import create_acces_token, decode_token, verify_password
from app.repositories.user_repository import UserRepository

class AuthService:

    @staticmethod
    async def login(db, email: str, password: str):
        user = await UserRepository.get_by_email(db, email)

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        access_token = create_acces_token(str(user.id))

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }

    @staticmethod
    async def get_current_user(db, token: str):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

        try:
            payload = decode_token(token)
            user_id = payload.get("sub")

            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = await UserRepository.get_by_id(db, user_id)

        if user is None:
            raise credentials_exception

        return user