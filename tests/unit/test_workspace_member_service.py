import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.workspace_member_service import WorkspaceMemberService

class FakeDb:
    pass

def test_normalize_email():
    assert WorkspaceMemberService._normalize_email("  USER@EXAMPLE.COM  ") == "user@example.com"


def test_ensure_owner_role_allows_owner():
    WorkspaceMemberService._ensure_owner_role("owner", detail="Only owner")


def test_ensure_owner_role_rejects_member():
    with pytest.raises(HTTPException) as exc:
        WorkspaceMemberService._ensure_owner_role("member", detail="Only owner")

    assert exc.value.status_code == 403
    assert exc.value.detail == "Only owner"


def test_ensure_not_owner_allows_member():
    WorkspaceMemberService._ensure_not_owner_membership(
        "member",
        detail="Owner cannot be removed",
    )


def test_ensure_not_owner_rejects_owner():
    with pytest.raises(HTTPException) as exc:
        WorkspaceMemberService._ensure_not_owner_membership(
            "owner",
            detail="Owner cannot be removed",
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_workspace_membership_or_404_rejects(monkeypatch):
    async def fake_get_by_workspace_and_user(db, workspace_id, user_id):
        return None

    monkeypatch.setattr(
        "app.services.workspace_member_service.WorkspaceMemberRepository.get_by_workspace_and_user",
        fake_get_by_workspace_and_user,
    )

    with pytest.raises(HTTPException) as exc:
        await WorkspaceMemberService._get_workspace_membership_or_404(
            db=FakeDb(),
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_user_by_email_or_404_rejects(monkeypatch):
    async def fake_get_by_email(db, email):
        return None

    monkeypatch.setattr(
        "app.services.workspace_member_service.UserRepository.get_by_email",
        fake_get_by_email,
    )

    with pytest.raises(HTTPException) as exc:
        await WorkspaceMemberService._get_user_by_email_or_404(
            db=FakeDb(),
            email="missing@example.com",
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found"


@pytest.mark.asyncio
async def test_ensure_not_workspace_member_rejects_existing(monkeypatch):
    async def fake_get_by_workspace_and_user(db, workspace_id, user_id):
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(
        "app.services.workspace_member_service.WorkspaceMemberRepository.get_by_workspace_and_user",
        fake_get_by_workspace_and_user,
    )

    with pytest.raises(HTTPException) as exc:
        await WorkspaceMemberService._ensure_not_workspace_member(
            db=FakeDb(),
            workspace_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_get_created_member_or_500_rejects(monkeypatch):
    async def fake_get_workspace_members(db, workspace_id):
        return []

    monkeypatch.setattr(
        "app.services.workspace_member_service.WorkspaceMemberRepository.get_workspace_members",
        fake_get_workspace_members,
    )

    with pytest.raises(HTTPException) as exc:
        await WorkspaceMemberService._get_created_member_or_500(
            db=FakeDb(),
            workspace_id=uuid.uuid4(),
            membership_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 500