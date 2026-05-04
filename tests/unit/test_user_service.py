import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.user_service import UserService


class FakeDb:
    async def commit(self):
        return None

    async def refresh(self, obj):
        return None


@pytest.mark.asyncio
async def test_create_user_duplicate_email(monkeypatch):
    existing_user = SimpleNamespace(id=uuid.uuid4())

    async def fake_get_by_email(db, email):
        return existing_user

    monkeypatch.setattr(
        "app.services.user_service.UserRepository.get_by_email",
        fake_get_by_email,
    )

    with pytest.raises(HTTPException) as exc:
        await UserService.create_user(
            FakeDb(),
            email="user@example.com",
            password="password123",
            display_name="User",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "User with this email already exists"


@pytest.mark.asyncio
async def test_create_user_success(monkeypatch):
    created_objects = []

    async def fake_get_by_email(db, email):
        return None

    def fake_hash_password(password):
        return "hashed-password"

    async def fake_create(db, user):
        created_objects.append(user)

    monkeypatch.setattr(
        "app.services.user_service.UserRepository.get_by_email",
        fake_get_by_email,
    )
    monkeypatch.setattr(
        "app.services.user_service.hash_password",
        fake_hash_password,
    )
    monkeypatch.setattr(
        "app.services.user_service.UserRepository.create",
        fake_create,
    )

    result = await UserService.create_user(
        FakeDb(),
        email="user@example.com",
        password="password123",
        display_name="User",
    )

    assert result.email == "user@example.com"
    assert result.password_hash == "hashed-password"
    assert result.display_name == "User"
    assert created_objects[0] == result