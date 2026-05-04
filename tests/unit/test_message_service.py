import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.message_service import MessageService

class FakeDb:
    pass

def test_normalize_content_strips_spaces():
    result = MessageService._normalize_content("  hello  ")

    assert result == "hello"


def test_normalize_content_rejects_empty_string():
    with pytest.raises(HTTPException) as exc:
        MessageService._normalize_content("   ")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Message can not be empty"


def test_find_message_in_payload_returns_item():
    message_id = uuid.uuid4()
    item = {
        "id": message_id,
        "content": "Hello",
    }

    result = MessageService._find_message_in_payload_or_500(
        messages=[item],
        message_id=message_id,
        detail="Not found",
    )

    assert result == item


def test_find_message_in_payload_raises_500():
    with pytest.raises(HTTPException) as exc:
        MessageService._find_message_in_payload_or_500(
            messages=[],
            message_id=uuid.uuid4(),
            detail="Message could not be loaded",
        )

    assert exc.value.status_code == 500
    assert exc.value.detail == "Message could not be loaded"


@pytest.mark.asyncio
async def test_ensure_channel_access_channel_not_found(monkeypatch):
    async def fake_get_by_id(db, channel_id):
        return None

    monkeypatch.setattr(
        "app.services.message_service.ChannelRepository.get_by_id",
        fake_get_by_id,
    )

    with pytest.raises(HTTPException) as exc:
        await MessageService._ensure_channel_access(
            db=FakeDb(),
            current_user=SimpleNamespace(id=uuid.uuid4()),
            channel_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ensure_channel_access_workspace_member_not_found(monkeypatch):
    channel = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        is_private=False,
    )

    async def fake_get_by_id(db, channel_id):
        return channel

    async def fake_is_user_member(db, workspace_id, user_id):
        return False

    monkeypatch.setattr(
        "app.services.message_service.ChannelRepository.get_by_id",
        fake_get_by_id,
    )
    monkeypatch.setattr(
        "app.services.message_service.WorkspaceRepository.is_user_member",
        fake_is_user_member,
    )

    with pytest.raises(HTTPException) as exc:
        await MessageService._ensure_channel_access(
            db=FakeDb(),
            current_user=SimpleNamespace(id=uuid.uuid4()),
            channel_id=channel.id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_ensure_channel_access_private_channel_member_not_found(monkeypatch):
    channel = SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        is_private=True,
    )

    async def fake_get_by_id(db, channel_id):
        return channel

    async def fake_workspace_is_user_member(db, workspace_id, user_id):
        return True

    async def fake_channel_is_user_member(db, channel_id, user_id):
        return False

    monkeypatch.setattr(
        "app.services.message_service.ChannelRepository.get_by_id",
        fake_get_by_id,
    )
    monkeypatch.setattr(
        "app.services.message_service.WorkspaceRepository.is_user_member",
        fake_workspace_is_user_member,
    )
    monkeypatch.setattr(
        "app.services.message_service.ChannelMemberRepository.is_user_member",
        fake_channel_is_user_member,
    )

    with pytest.raises(HTTPException) as exc:
        await MessageService._ensure_channel_access(
            db=FakeDb(),
            current_user=SimpleNamespace(id=uuid.uuid4()),
            channel_id=channel.id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_accessible_message_not_found(monkeypatch):
    async def fake_get_by_id(db, message_id):
        return None

    monkeypatch.setattr(
        "app.services.message_service.MessageRepository.get_by_id",
        fake_get_by_id,
    )

    with pytest.raises(HTTPException) as exc:
        await MessageService._get_accessible_message(
            db=FakeDb(),
            current_user=SimpleNamespace(id=uuid.uuid4()),
            message_id=uuid.uuid4(),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Message not found"


@pytest.mark.asyncio
async def test_ensure_message_belongs_to_channel_rejects(monkeypatch):
    channel_id = uuid.uuid4()
    message = SimpleNamespace(
        id=uuid.uuid4(),
        channel_id=uuid.uuid4(),
    )

    async def fake_get_accessible_message(db, current_user, message_id):
        return message

    monkeypatch.setattr(
        MessageService,
        "_get_accessible_message",
        fake_get_accessible_message,
    )

    with pytest.raises(HTTPException) as exc:
        await MessageService._ensure_message_belongs_to_channel(
            db=FakeDb(),
            current_user=SimpleNamespace(id=uuid.uuid4()),
            message_id=message.id,
            channel_id=channel_id,
            field_name="after",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "'after' message does not belong to this channel"


@pytest.mark.asyncio
async def test_list_messages_before_and_after_rejected(monkeypatch):
    async def fake_ensure_channel_access(db, current_user, channel_id):
        return None

    monkeypatch.setattr(
        MessageService,
        "_ensure_channel_access",
        fake_ensure_channel_access,
    )

    with pytest.raises(HTTPException) as exc:
        await MessageService.list_messages(
            db=FakeDb(),
            current_user=SimpleNamespace(id=uuid.uuid4()),
            channel_id=uuid.uuid4(),
            before=uuid.uuid4(),
            after=uuid.uuid4(),
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Cannot use 'before' and 'after' together"


@pytest.mark.asyncio
async def test_update_message_forbidden_other_author(monkeypatch):
    current_user = SimpleNamespace(id=uuid.uuid4())
    message = SimpleNamespace(
        id=uuid.uuid4(),
        author_id=uuid.uuid4(),
        deleted_at=None,
    )

    async def fake_get_accessible_message(db, current_user, message_id):
        return message

    monkeypatch.setattr(
        MessageService,
        "_get_accessible_message",
        fake_get_accessible_message,
    )

    with pytest.raises(HTTPException) as exc:
        await MessageService.update_message(
            db=FakeDb(),
            current_user=current_user,
            message_id=message.id,
            content="Updated",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_deleted_message_rejected(monkeypatch):
    current_user = SimpleNamespace(id=uuid.uuid4())
    message = SimpleNamespace(
        id=uuid.uuid4(),
        author_id=current_user.id,
        deleted_at=object(),
    )

    async def fake_get_accessible_message(db, current_user, message_id):
        return message

    monkeypatch.setattr(
        MessageService,
        "_get_accessible_message",
        fake_get_accessible_message,
    )

    with pytest.raises(HTTPException) as exc:
        await MessageService.update_message(
            db=FakeDb(),
            current_user=current_user,
            message_id=message.id,
            content="Updated",
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Deleted message cannot be edited"


@pytest.mark.asyncio
async def test_delete_message_forbidden_other_author(monkeypatch):
    current_user = SimpleNamespace(id=uuid.uuid4())
    message = SimpleNamespace(
        id=uuid.uuid4(),
        author_id=uuid.uuid4(),
        deleted_at=None,
    )

    async def fake_get_accessible_message(db, current_user, message_id):
        return message

    monkeypatch.setattr(
        MessageService,
        "_get_accessible_message",
        fake_get_accessible_message,
    )

    with pytest.raises(HTTPException) as exc:
        await MessageService.delete_message(
            db=FakeDb(),
            current_user=current_user,
            message_id=message.id,
        )

    assert exc.value.status_code == 403