from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace_member import WorkspaceMember
from app.models.user import User

class WorkspaceMemberRepository:

    @staticmethod
    async def get_workspace_members(
        db: AsyncSession,
        workspace_id: UUID,
    ) -> list[dict]:
        result = await db.execute(
            select(
                WorkspaceMember,
                User.display_name,
            )
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.created_at.asc())
        )

        rows = result.all()

        return [
            {
                "id": member.id,
                "workspace_id": member.workspace_id,
                "user_id": member.user_id,
                "role": member.role,
                "display_name": display_name,
            }
            for member, display_name in rows
        ]

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