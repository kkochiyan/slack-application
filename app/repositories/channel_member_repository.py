from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel_member import ChannelMember

class ChannelMemberRepository:

    @staticmethod
    async def is_user_member(
            db: AsyncSession,
            channel_id: UUID,
            user_id: UUID,
    ) -> bool:
        result = await db.execute(
            select(
                exists().where(
                    ChannelMember.channel_id == channel_id,
                    ChannelMember.user_id == user_id,
                )
            )
        )
        return bool(result.scalar())

    @staticmethod
    async def get_channel_members(
            db: AsyncSession,
            channel_id: UUID,
    ) -> list[ChannelMember]:
        result = await db.execute(
            select(ChannelMember)
            .where(ChannelMember.channel_id == channel_id)
            .order_by(ChannelMember.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def add(db: AsyncSession, membership: ChannelMember) -> None:
        db.add(membership)

    @staticmethod
    async def get_by_channel_and_user(
            db: AsyncSession,
            channel_id: UUID,
            user_id: UUID,
    ) -> ChannelMember | None:
        result = await db.execute(
            select(ChannelMember).where(
                ChannelMember.channel_id == channel_id,
                ChannelMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete(db: AsyncSession, membership: ChannelMember) -> None:
        await db.delete(membership)