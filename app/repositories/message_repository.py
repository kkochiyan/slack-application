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
        before: UUID | None = None,
        after: UUID | None = None,
    ) -> list[Message]:
        query = (
            select(Message)
            .where(
                Message.channel_id == channel_id,
                Message.deleted_at.is_(None),
            )
        )

        if before is not None:
            before_message = await MessageRepository.get_by_id(db, before)
            if before_message is not None:
                query = query.where(Message.created_at < before_message.created_at)

        if after is not None:
            after_message = await MessageRepository.get_by_id(db, after)
            if after_message is not None:
                query = query.where(Message.created_at > after_message.created_at)

        query = query.order_by(Message.created_at.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())