import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.channel_member_service import ChannelMemberService

class FakeDb:
    pass

class FakeChannel:
    def __init__(self, is_private: bool):
        self.is_private = is_private


class FakeMembership:
    def __init__(self, role: str):
        self.role = role


def test_normalize_email():
    assert ChannelMemberService._normalize_email("  USER@EXAMPLE.COM  ") == "user@example.com"


def test_ensure_private_channel_allows_private():
    ChannelMemberService._ensure_private_channel(
        FakeChannel(is_private=True),
        detail="Private only",
    )


def test_ensure_private_channel_rejects_public():
    with pytest.raises(HTTPException) as exc:
        ChannelMemberService._ensure_private_channel(
            FakeChannel(is_private=False),
            detail="Private only",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Private only"


def test_ensure_owner_role_allows_owner():
    ChannelMemberService._ensure_owner_role(
        FakeMembership(role="owner"),
        detail="Only owner",
    )


def test_ensure_owner_role_rejects_member():
    with pytest.raises(HTTPException) as exc:
        ChannelMemberService._ensure_owner_role(
            FakeMembership(role="member"),
            detail="Only owner",
        )

    assert exc.value.status_code == 403


def test_ensure_not_owner_allows_member():
    ChannelMemberService._ensure_not_owner_membership(
        FakeMembership(role="member"),
        detail="Owner cannot be removed",
    )


def test_ensure_not_owner_rejects_owner():
    with pytest.raises(HTTPException) as exc:
        ChannelMemberService._ensure_not_owner_membership(
            FakeMembership(role="owner"),
            detail="Owner cannot be removed",
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_channel_or_404_rejects(monkeypatch):
    async def fake_get_by_id(db, channel_id):
        return None

    monkeypatch.setattr(
        "app.services.channel_member_service.ChannelRepository.get_by_id",
        fake_get_by_id,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelMemberService._get_channel_or_404(FakeDb(), uuid.uuid4())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ensure_workspace_member_or_404_rejects(monkeypatch):
    async def fake_is_user_member(db, workspace_id, user_id):
        return False

    monkeypatch.setattr(
        "app.services.channel_member_service.WorkspaceRepository.is_user_member",
        fake_is_user_member,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelMemberService._ensure_workspace_member_or_404(
            db=FakeDb(),
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            detail="Channel not found",
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ensure_workspace_member_or_400_rejects(monkeypatch):
    async def fake_is_user_member(db, workspace_id, user_id):
        return False

    monkeypatch.setattr(
        "app.services.channel_member_service.WorkspaceRepository.is_user_member",
        fake_is_user_member,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelMemberService._ensure_workspace_member_or_400(
            db=FakeDb(),
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            detail="User is not a member of this workspace",
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_ensure_channel_member_or_404_rejects(monkeypatch):
    async def fake_is_user_member(db, channel_id, user_id):
        return False

    monkeypatch.setattr(
        "app.services.channel_member_service.ChannelMemberRepository.is_user_member",
        fake_is_user_member,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelMemberService._ensure_channel_member_or_404(
            db=FakeDb(),
            channel_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            detail="Channel not found",
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_membership_or_404_rejects(monkeypatch):
    async def fake_get_by_channel_and_user(db, channel_id, user_id):
        return None

    monkeypatch.setattr(
        "app.services.channel_member_service.ChannelMemberRepository.get_by_channel_and_user",
        fake_get_by_channel_and_user,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelMemberService._get_membership_or_404(
            db=FakeDb(),
            channel_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            detail="Channel member not found",
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_membership_or_403_rejects(monkeypatch):
    async def fake_get_by_channel_and_user(db, channel_id, user_id):
        return None

    monkeypatch.setattr(
        "app.services.channel_member_service.ChannelMemberRepository.get_by_channel_and_user",
        fake_get_by_channel_and_user,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelMemberService._get_membership_or_403(
            db=FakeDb(),
            channel_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            detail="Forbidden",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_user_by_email_or_404_rejects(monkeypatch):
    async def fake_get_by_email(db, email):
        return None

    monkeypatch.setattr(
        "app.services.channel_member_service.UserRepository.get_by_email",
        fake_get_by_email,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelMemberService._get_user_by_email_or_404(
            db=FakeDb(),
            email="missing@example.com",
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ensure_not_channel_member_rejects_existing(monkeypatch):
    async def fake_get_by_channel_and_user(db, channel_id, user_id):
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(
        "app.services.channel_member_service.ChannelMemberRepository.get_by_channel_and_user",
        fake_get_by_channel_and_user,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelMemberService._ensure_not_channel_member(
            db=FakeDb(),
            channel_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            detail="Already member",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_get_created_member_or_500_rejects(monkeypatch):
    async def fake_get_channel_members(db, channel_id):
        return []

    monkeypatch.setattr(
        "app.services.channel_member_service.ChannelMemberRepository.get_channel_members",
        fake_get_channel_members,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelMemberService._get_created_member_or_500(
            db=FakeDb(),
            channel_id=uuid.uuid4(),
            membership_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 500