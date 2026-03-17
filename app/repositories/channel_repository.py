from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel

class ChannelRepository:

    @staticmethod
    async def get_by_id(db: AsyncSession, channel_id: UUID) -> Channel | None:
        result = await db.execute(
            select(Channel).where(Channel.id == channel_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_workspace_and_name(
            db: AsyncSession,
            workspace_id: UUID,
            name: str
    ) -> Channel | None:
        result = await db.execute(
            select(Channel).where(
                Channel.workspace_id == workspace_id,
                Channel.name == name,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_workspace_channels(
            db: AsyncSession,
            workspace_id: UUID,
    ) -> list[Channel]:
        result = await db.execute(
            select(Channel)
            .where(Channel.workspace_id == workspace_id)
            .order_by(Channel.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def add(db: AsyncSession, channel: Channel) -> None:
        db.add(channel)