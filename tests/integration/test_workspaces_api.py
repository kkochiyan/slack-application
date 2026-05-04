import pytest

async def create_workspace(client, auth_headers):
    response = await client.post(
        "/workspaces",
        json={
            "name": "My Workspace",
            "slug": "my-workspace",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_create_workspace(client, auth_headers):
    data = await create_workspace(client, auth_headers)

    assert data["name"] == "My Workspace"
    assert data["slug"] == "my-workspace"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_workspaces(client, auth_headers):
    await create_workspace(client, auth_headers)

    response = await client.get(
        "/workspaces",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "my-workspace"


@pytest.mark.asyncio
async def test_create_duplicate_workspace_slug_returns_409(client, auth_headers):
    await create_workspace(client, auth_headers)

    response = await client.post(
        "/workspaces",
        json={
            "name": "Another Workspace",
            "slug": "my-workspace",
        },
        headers=auth_headers,
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_delete_workspace(client, auth_headers):
    workspace = await create_workspace(client, auth_headers)

    response = await client.delete(
        f"/workspaces/{workspace['id']}",
        headers=auth_headers,
    )

    assert response.status_code == 204

    list_response = await client.get(
        "/workspaces",
        headers=auth_headers,
    )

    assert list_response.status_code == 200
    assert list_response.json() == []