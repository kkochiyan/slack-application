import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from jose import JWTError

from app.services.auth_service import AuthService

class FakeDb:
    pass

@pytest.mark.asyncio
async def test_login_invalid_email(monkeypatch):
    async def fake_get_by_email(db, email):
        return None

    monkeypatch.setattr(
        "app.services.auth_service.UserRepository.get_by_email",
        fake_get_by_email,
    )

    with pytest.raises(HTTPException) as exc:
        await AuthService.login(FakeDb(), "bad@example.com", "password123")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_invalid_password(monkeypatch):
    user = SimpleNamespace(id=uuid.uuid4(), password_hash="hashed")

    async def fake_get_by_email(db, email):
        return user

    def fake_verify_password(password, password_hash):
        return False

    monkeypatch.setattr(
        "app.services.auth_service.UserRepository.get_by_email",
        fake_get_by_email,
    )
    monkeypatch.setattr(
        "app.services.auth_service.verify_password",
        fake_verify_password,
    )

    with pytest.raises(HTTPException) as exc:
        await AuthService.login(FakeDb(), "user@example.com", "wrong")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_success(monkeypatch):
    user = SimpleNamespace(id=uuid.uuid4(), password_hash="hashed")

    async def fake_get_by_email(db, email):
        return user

    def fake_verify_password(password, password_hash):
        return True

    def fake_create_token(user_id):
        return "test-token"

    monkeypatch.setattr(
        "app.services.auth_service.UserRepository.get_by_email",
        fake_get_by_email,
    )
    monkeypatch.setattr(
        "app.services.auth_service.verify_password",
        fake_verify_password,
    )
    monkeypatch.setattr(
        "app.services.auth_service.create_acces_token",
        fake_create_token,
    )

    result = await AuthService.login(FakeDb(), "user@example.com", "password123")

    assert result["access_token"] == "test-token"
    assert result["token_type"] == "bearer"
    assert result["user"] == user


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(monkeypatch):
    def fake_decode_token(token):
        raise JWTError("bad token")

    monkeypatch.setattr(
        "app.services.auth_service.decode_token",
        fake_decode_token,
    )

    with pytest.raises(HTTPException) as exc:
        await AuthService.get_current_user(FakeDb(), "bad-token")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_without_sub(monkeypatch):
    def fake_decode_token(token):
        return {}

    monkeypatch.setattr(
        "app.services.auth_service.decode_token",
        fake_decode_token,
    )

    with pytest.raises(HTTPException) as exc:
        await AuthService.get_current_user(FakeDb(), "token")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(monkeypatch):
    def fake_decode_token(token):
        return {"sub": str(uuid.uuid4())}

    async def fake_get_by_id(db, user_id):
        return None

    monkeypatch.setattr(
        "app.services.auth_service.decode_token",
        fake_decode_token,
    )
    monkeypatch.setattr(
        "app.services.auth_service.UserRepository.get_by_id",
        fake_get_by_id,
    )

    with pytest.raises(HTTPException) as exc:
        await AuthService.get_current_user(FakeDb(), "token")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_success(monkeypatch):
    user = SimpleNamespace(id=uuid.uuid4())

    def fake_decode_token(token):
        return {"sub": str(user.id)}

    async def fake_get_by_id(db, user_id):
        return user

    monkeypatch.setattr(
        "app.services.auth_service.decode_token",
        fake_decode_token,
    )
    monkeypatch.setattr(
        "app.services.auth_service.UserRepository.get_by_id",
        fake_get_by_id,
    )

    result = await AuthService.get_current_user(FakeDb(), "token")

    assert result == user