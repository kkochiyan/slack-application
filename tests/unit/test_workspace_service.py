import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.services.workspace_service import WorkspaceService

class FakeDb:
    def __init__(self):
        self.added = []
        self.committed = False
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        return None

    async def rollback(self):
        self.rolled_back = True


def test_normalize_name():
    assert WorkspaceService._normalize_name("  My Workspace  ") == "My Workspace"


def test_normalize_slug():
    assert WorkspaceService._normalize_slug("  My Company  ") == "my-company"


def test_ensure_not_empty_raises_400():
    with pytest.raises(HTTPException) as exc:
        WorkspaceService._ensure_not_empty("", detail="Empty value")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Empty value"


@pytest.mark.asyncio
async def test_get_workspace_or_404_not_found(monkeypatch):
    async def fake_get_by_id(db, workspace_id):
        return None

    monkeypatch.setattr(
        "app.services.workspace_service.WorkspaceRepository.get_by_id",
        fake_get_by_id,
    )

    with pytest.raises(HTTPException) as exc:
        await WorkspaceService._get_workspace_or_404(FakeDb(), uuid.uuid4())

    assert exc.value.status_code == 404
    assert exc.value.detail == "Workspace not found"


@pytest.mark.asyncio
async def test_get_workspace_or_404_success(monkeypatch):
    workspace = SimpleNamespace(id=uuid.uuid4())

    async def fake_get_by_id(db, workspace_id):
        return workspace

    monkeypatch.setattr(
        "app.services.workspace_service.WorkspaceRepository.get_by_id",
        fake_get_by_id,
    )

    result = await WorkspaceService._get_workspace_or_404(FakeDb(), workspace.id)

    assert result == workspace


@pytest.mark.asyncio
async def test_get_user_workspace_by_id_not_found(monkeypatch):
    current_user = SimpleNamespace(id=uuid.uuid4())

    async def fake_get_user_workspace_by_id(db, workspace_id, user_id):
        return None

    monkeypatch.setattr(
        "app.services.workspace_service.WorkspaceRepository.get_user_workspace_by_id",
        fake_get_user_workspace_by_id,
    )

    with pytest.raises(HTTPException) as exc:
        await WorkspaceService.get_user_workspace_by_id(
            db=FakeDb(),
            workspace_id=uuid.uuid4(),
            current_user=current_user,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_workspace_forbidden(monkeypatch):
    current_user = SimpleNamespace(id=uuid.uuid4())
    workspace = SimpleNamespace(id=uuid.uuid4(), owner_id=uuid.uuid4())

    async def fake_get_workspace_or_404(db, workspace_id):
        return workspace

    monkeypatch.setattr(
        WorkspaceService,
        "_get_workspace_or_404",
        fake_get_workspace_or_404,
    )

    with pytest.raises(HTTPException) as exc:
        await WorkspaceService.delete_workspace(
            db=FakeDb(),
            current_user=current_user,
            workspace_id=workspace.id,
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Only workspace owner can delete workspace"


@pytest.mark.asyncio
async def test_create_workspace_duplicate_slug(monkeypatch):
    current_user = SimpleNamespace(id=uuid.uuid4())

    async def fake_get_by_slug(db, slug):
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(
        "app.services.workspace_service.WorkspaceRepository.get_by_slug",
        fake_get_by_slug,
    )

    with pytest.raises(HTTPException) as exc:
        await WorkspaceService.create_workspace(
            db=FakeDb(),
            current_user=current_user,
            name="My Workspace",
            slug="my-workspace",
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_workspace_integrity_error(monkeypatch):
    current_user = SimpleNamespace(id=uuid.uuid4())
    db = FakeDb()

    async def fake_get_by_slug(db, slug):
        return None

    async def fake_commit():
        raise IntegrityError("statement", "params", "orig")

    monkeypatch.setattr(
        "app.services.workspace_service.WorkspaceRepository.get_by_slug",
        fake_get_by_slug,
    )
    db.commit = fake_commit

    with pytest.raises(HTTPException) as exc:
        await WorkspaceService.create_workspace(
            db=db,
            current_user=current_user,
            name="My Workspace",
            slug="my-workspace",
        )

    assert exc.value.status_code == 409
    assert db.rolled_back is True