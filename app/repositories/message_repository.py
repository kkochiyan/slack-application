from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message

class MessageRepository:

    @staticmethod
    async def add(db: AsyncSession, message: Message) -> None:
        db.add(message)

    @staticmethod
    async def get_by_id(db: AsyncSession, message_id: UUID) -> Message | None:
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_channel_messages(
            db: AsyncSession,
            channel_id: UUID,
            limit: int = 50,
    ) -> list[Message]:
        result = await db.execute(
            select(Message)
            .where(
                Message.channel_id == channel_id,
                Message.deleted_at.is_(None),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())