import pytest

async def create_workspace(client, auth_headers):
    response = await client.post(
        "/workspaces",
        headers=auth_headers,
        json={
            "name": "My Workspace",
            "slug": "my-workspace",
        },
    )

    assert response.status_code == 200
    return response.json()


async def create_channel(client, auth_headers, workspace_id):
    response = await client.post(
        f"/workspaces/{workspace_id}/channels",
        headers=auth_headers,
        json={
            "name": "general",
            "description": "Main channel",
            "is_private": False,
        },
    )

    assert response.status_code == 200
    return response.json()


@pytest.fixture(autouse=True)
def mock_redis_publish(monkeypatch):
    from app.core.redis_client import redis_client

    async def fake_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(redis_client, "publish", fake_publish)


@pytest.mark.asyncio
async def test_create_message(client, auth_headers):
    workspace = await create_workspace(client, auth_headers)
    channel = await create_channel(client, auth_headers, workspace["id"])

    response = await client.post(
        f"/channels/{channel['id']}/messages",
        headers=auth_headers,
        json={
            "content": "Hello world",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["content"] == "Hello world"
    assert data["message_type"] == "text"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_messages(client, auth_headers):
    workspace = await create_workspace(client, auth_headers)
    channel = await create_channel(client, auth_headers, workspace["id"])

    await client.post(
        f"/channels/{channel['id']}/messages",
        headers=auth_headers,
        json={
            "content": "Hello world",
        },
    )

    response = await client.get(
        f"/channels/{channel['id']}/messages",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "Hello world"


@pytest.mark.asyncio
async def test_update_message(client, auth_headers):
    workspace = await create_workspace(client, auth_headers)
    channel = await create_channel(client, auth_headers, workspace["id"])

    create_response = await client.post(
        f"/channels/{channel['id']}/messages",
        headers=auth_headers,
        json={
            "content": "Original message",
        },
    )

    message = create_response.json()

    update_response = await client.patch(
        f"/messages/{message['id']}",
        headers=auth_headers,
        json={
            "content": "Updated message",
        },
    )

    assert update_response.status_code == 200

    data = update_response.json()
    assert data["content"] == "Updated message"
    assert data["edited_at"] is not None


@pytest.mark.asyncio
async def test_delete_message(client, auth_headers):
    workspace = await create_workspace(client, auth_headers)
    channel = await create_channel(client, auth_headers, workspace["id"])

    create_response = await client.post(
        f"/channels/{channel['id']}/messages",
        headers=auth_headers,
        json={
            "content": "Message to delete",
        },
    )

    message = create_response.json()

    delete_response = await client.delete(
        f"/messages/{message['id']}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 204

    list_response = await client.get(
        f"/channels/{channel['id']}/messages",
        headers=auth_headers,
    )

    assert list_response.status_code == 200

    data = list_response.json()
    assert data == []


@pytest.mark.asyncio
async def test_empty_message_returns_400(client, auth_headers):
    workspace = await create_workspace(client, auth_headers)
    channel = await create_channel(client, auth_headers, workspace["id"])

    response = await client.post(
        f"/channels/{channel['id']}/messages",
        headers=auth_headers,
        json={
            "content": "   ",
        },
    )

    assert response.status_code == 400