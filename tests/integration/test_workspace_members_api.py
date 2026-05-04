import pytest

async def register_and_login(client, email, display_name):
    await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "display_name": display_name,
        },
    )

    response = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "password123",
        },
    )

    token = response.json()["access_token"]
    user = response.json()["user"]

    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user": user,
    }


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


@pytest.mark.asyncio
async def test_list_workspace_members(client):
    owner = await register_and_login(client, "owner@example.com", "Owner")
    workspace = await create_workspace(client, owner["headers"])

    response = await client.get(
        f"/workspaces/{workspace['id']}/members",
        headers=owner["headers"],
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == owner["user"]["id"]
    assert data[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_add_workspace_member(client):
    owner = await register_and_login(client, "owner@example.com", "Owner")
    await register_and_login(client, "member@example.com", "Member")

    workspace = await create_workspace(client, owner["headers"])

    response = await client.post(
        f"/workspaces/{workspace['id']}/members",
        headers=owner["headers"],
        json={
            "email": "member@example.com",
        },
    )

    assert response.status_code in (200, 201)

    data = response.json()
    assert data["role"] == "member"
    assert data["display_name"] == "Member"


@pytest.mark.asyncio
async def test_add_duplicate_workspace_member_returns_409(client):
    owner = await register_and_login(client, "owner@example.com", "Owner")
    await register_and_login(client, "member@example.com", "Member")

    workspace = await create_workspace(client, owner["headers"])

    first_response = await client.post(
        f"/workspaces/{workspace['id']}/members",
        headers=owner["headers"],
        json={
            "email": "member@example.com",
        },
    )
    assert first_response.status_code in (200, 201)

    second_response = await client.post(
        f"/workspaces/{workspace['id']}/members",
        headers=owner["headers"],
        json={
            "email": "member@example.com",
        },
    )

    assert second_response.status_code == 409


@pytest.mark.asyncio
async def test_remove_workspace_member(client):
    owner = await register_and_login(client, "owner@example.com", "Owner")
    member = await register_and_login(client, "member@example.com", "Member")

    workspace = await create_workspace(client, owner["headers"])

    add_response = await client.post(
        f"/workspaces/{workspace['id']}/members",
        headers=owner["headers"],
        json={
            "email": "member@example.com",
        },
    )
    assert add_response.status_code in (200, 201)

    remove_response = await client.delete(
        f"/workspaces/{workspace['id']}/members/{member['user']['id']}",
        headers=owner["headers"],
    )

    assert remove_response.status_code == 204

    list_response = await client.get(
        f"/workspaces/{workspace['id']}/members",
        headers=owner["headers"],
    )

    data = list_response.json()
    assert len(data) == 1
    assert data[0]["role"] == "owner"


@pytest.mark.asyncio
async def test_non_owner_cannot_add_workspace_member(client):
    owner = await register_and_login(client, "owner@example.com", "Owner")
    member = await register_and_login(client, "member@example.com", "Member")
    await register_and_login(client, "third@example.com", "Third")

    workspace = await create_workspace(client, owner["headers"])

    await client.post(
        f"/workspaces/{workspace['id']}/members",
        headers=owner["headers"],
        json={
            "email": "member@example.com",
        },
    )

    response = await client.post(
        f"/workspaces/{workspace['id']}/members",
        headers=member["headers"],
        json={
            "email": "third@example.com",
        },
    )

    assert response.status_code == 403