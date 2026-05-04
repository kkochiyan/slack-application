import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:postgres@localhost:5433/messenger_test"
)
os.environ["JWT_SECRET"] = "test_secret"
os.environ["DEBUG"] = "false"

from app.db.base import Base
from app.db.session import get_db
from app.main import create_application

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.channel import Channel
from app.models.channel_member import ChannelMember
from app.models.message import Message

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_engine):
    TestingSessionLocal = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    app = create_application()

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def auth_headers(client):
    await client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "display_name": "Test",
        },
    )

    response = await client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123",
        },

    )

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }