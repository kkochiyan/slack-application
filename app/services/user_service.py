from fastapi import HTTPException, status

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password

class UserService:

    @staticmethod
    async def create_user(db, email: str, password: str, display_name: str):
        existing_user = await UserRepository.get_by_email(db, email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        hashed = hash_password(password)

        user = User(
            email=email,
            password_hash=hashed,
            display_name=display_name,
        )

        await UserRepository.create(db, user)
        await db.commit()
        await db.refresh(user)
        return user