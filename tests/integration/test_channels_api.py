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


@pytest.mark.asyncio
async def test_create_channel(client, auth_headers):
    workspace = await create_workspace(client, auth_headers)

    channel = await create_channel(
        client=client,
        auth_headers=auth_headers,
        workspace_id=workspace["id"],
    )

    assert channel["name"] == "general"
    assert channel["description"] == "Main channel"
    assert channel["is_private"] is False
    assert "id" in channel


@pytest.mark.asyncio
async def test_list_channels(client, auth_headers):
    workspace = await create_workspace(client, auth_headers)

    await create_channel(
        client=client,
        auth_headers=auth_headers,
        workspace_id=workspace["id"],
    )

    response = await client.get(
        f"/workspaces/{workspace['id']}/channels",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "general"


@pytest.mark.asyncio
async def test_create_duplicate_channel_name_returns_409(client, auth_headers):
    workspace = await create_workspace(client, auth_headers)

    await create_channel(
        client=client,
        auth_headers=auth_headers,
        workspace_id=workspace["id"],
    )

    response = await client.post(
        f"/workspaces/{workspace['id']}/channels",
        headers=auth_headers,
        json={
            "name": "general",
            "description": "Duplicate",
            "is_private": False,
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_delete_channel(client, auth_headers):
    workspace = await create_workspace(client, auth_headers)
    channel = await create_channel(client, auth_headers, workspace["id"])

    response = await client.delete(
        f"/channels/{channel['id']}",
        headers=auth_headers,
    )

    assert response.status_code == 204

    list_response = await client.get(
        f"/workspaces/{workspace['id']}/channels",
        headers=auth_headers,
    )

    assert list_response.status_code == 200
    assert list_response.json() == []