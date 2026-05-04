import pytest

@pytest.mark.asyncio
async def test_register_user(client):
    response = await client.post(
        "/auth/register",
        json={
            "email": "karen@example.com",
            "password": "password123",
            "display_name": "Karen",
        },
    )

    assert response.status_code in (200, 201)

    data = response.json()
    assert data["email"] == "karen@example.com"
    assert data["display_name"] == "Karen"
    assert "id" in data


@pytest.mark.asyncio
async def test_login_user(client):
    await client.post(
        "/auth/register",
        json={
            "email": "karen@example.com",
            "password": "password123",
            "display_name": "Karen",
        },
    )

    response = await client.post(
        "/auth/login",
        json={
            "email": "karen@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "karen@example.com"
    assert data["user"]["display_name"] == "Karen"
    assert "id" in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_conflict(client):
    payload = {
        "email": "karen@example.com",
        "password": "password123",
        "display_name": "Karen",
    }

    first_response = await client.post("/auth/register", json=payload)
    assert first_response.status_code in (200, 201)

    second_response = await client.post("/auth/register", json=payload)
    assert second_response.status_code == 409