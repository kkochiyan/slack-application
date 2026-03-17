from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace_member import WorkspaceMember

class WorkspaceMemberRepository:

    @staticmethod
    async def get_workspace_members(
            db: AsyncSession,
            workspace_id: UUID,
    ) -> list[WorkspaceMember]:
        result = await db.execute(
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_workspace_and_user(
            db: AsyncSession,
            workspace_id: UUID,
            user_id: UUID,
    ) -> WorkspaceMember | None:
        result = await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def add(db: AsyncSession, membership: WorkspaceMember) -> None:
        db.add(membership)

    @staticmethod
    async def delete(db: AsyncSession, membership: WorkspaceMember) -> None:
        await db.delete(membership)