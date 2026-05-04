import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.services.channel_service import ChannelService

class FakeDb:
    def __init__(self):
        self.added = []
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def rollback(self):
        self.rolled_back = True

def test_normalize_channel_name():
    assert ChannelService._normalize_channel_name("  GENERAL  ") == "general"


def test_normalize_description_none():
    assert ChannelService._normalize_description(None) is None


def test_normalize_description_empty_to_none():
    assert ChannelService._normalize_description("   ") is None


def test_normalize_description_strips_text():
    assert ChannelService._normalize_description("  Main channel  ") == "Main channel"


def test_ensure_workspace_owner_allows_owner():
    ChannelService._ensure_workspace_owner("owner", detail="Only owner")


def test_ensure_workspace_owner_rejects_member():
    with pytest.raises(HTTPException) as exc:
        ChannelService._ensure_workspace_owner("member", detail="Only owner")

    assert exc.value.status_code == 403
    assert exc.value.detail == "Only owner"


@pytest.mark.asyncio
async def test_get_channel_or_404_not_found(monkeypatch):
    async def fake_get_by_id(db, channel_id):
        return None

    monkeypatch.setattr(
        "app.services.channel_service.ChannelRepository.get_by_id",
        fake_get_by_id,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelService._get_channel_or_404(FakeDb(), uuid.uuid4())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ensure_workspace_member_or_404_rejects(monkeypatch):
    async def fake_is_user_member(db, workspace_id, user_id):
        return False

    monkeypatch.setattr(
        "app.services.channel_service.WorkspaceRepository.is_user_member",
        fake_is_user_member,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelService._ensure_workspace_member_or_404(
            db=FakeDb(),
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            detail="Workspace not found",
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Workspace not found"


@pytest.mark.asyncio
async def test_get_workspace_membership_or_404_rejects(monkeypatch):
    async def fake_get_by_workspace_and_user(db, workspace_id, user_id):
        return None

    monkeypatch.setattr(
        "app.services.channel_service.WorkspaceMemberRepository.get_by_workspace_and_user",
        fake_get_by_workspace_and_user,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelService._get_workspace_membership_or_404(
            db=FakeDb(),
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_accessible_private_channel_not_member(monkeypatch):
    channel = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        is_private=True,
    )

    async def fake_get_channel_or_404(db, channel_id):
        return channel

    async def fake_ensure_workspace_member_or_404(db, workspace_id, user_id, detail):
        return None

    async def fake_is_user_member(db, channel_id, user_id):
        return False

    monkeypatch.setattr(ChannelService, "_get_channel_or_404", fake_get_channel_or_404)
    monkeypatch.setattr(
        ChannelService,
        "_ensure_workspace_member_or_404",
        fake_ensure_workspace_member_or_404,
    )
    monkeypatch.setattr(
        "app.services.channel_service.ChannelMemberRepository.is_user_member",
        fake_is_user_member,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelService._get_accessible_channel_or_404(
            db=FakeDb(),
            channel_id=channel.id,
            user_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_channel_duplicate_name(monkeypatch):
    current_user = SimpleNamespace(id=uuid.uuid4())
    membership = SimpleNamespace(role="owner")

    async def fake_get_workspace_membership_or_404(db, workspace_id, user_id):
        return membership

    async def fake_get_by_workspace_and_name(db, workspace_id, name):
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(
        ChannelService,
        "_get_workspace_membership_or_404",
        fake_get_workspace_membership_or_404,
    )
    monkeypatch.setattr(
        "app.services.channel_service.ChannelRepository.get_by_workspace_and_name",
        fake_get_by_workspace_and_name,
    )

    with pytest.raises(HTTPException) as exc:
        await ChannelService.create_channel(
            db=FakeDb(),
            current_user=current_user,
            workspace_id=uuid.uuid4(),
            name="general",
            description=None,
            is_private=False,
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_channel_integrity_error(monkeypatch):
    current_user = SimpleNamespace(id=uuid.uuid4())
    membership = SimpleNamespace(role="owner")
    db = FakeDb()

    async def fake_get_workspace_membership_or_404(db, workspace_id, user_id):
        return membership

    async def fake_get_by_workspace_and_name(db, workspace_id, name):
        return None

    async def fake_commit():
        raise IntegrityError("statement", "params", "orig")

    monkeypatch.setattr(
        ChannelService,
        "_get_workspace_membership_or_404",
        fake_get_workspace_membership_or_404,
    )
    monkeypatch.setattr(
        "app.services.channel_service.ChannelRepository.get_by_workspace_and_name",
        fake_get_by_workspace_and_name,
    )

    db.commit = fake_commit

    with pytest.raises(HTTPException) as exc:
        await ChannelService.create_channel(
            db=db,
            current_user=current_user,
            workspace_id=uuid.uuid4(),
            name="general",
            description=None,
            is_private=False,
        )

    assert exc.value.status_code == 409
    assert db.rolled_back is True