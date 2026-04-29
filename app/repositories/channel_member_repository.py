from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel_member import ChannelMember
from app.models.user import User

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
    ) -> list[dict]:
        result = await db.execute(
            select(
                ChannelMember.id,
                ChannelMember.channel_id,
                ChannelMember.user_id,
                User.display_name.label("display_name"),
                ChannelMember.role,
            )
            .join(User, User.id == ChannelMember.user_id)
            .where(ChannelMember.channel_id == channel_id)
            .order_by(ChannelMember.created_at.asc())
        )
        return [dict(row._mapping) for row in result.all()]

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