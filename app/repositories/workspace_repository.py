from uuid import UUID

from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember

class WorkspaceRepository:

    @staticmethod
    async def get_by_slug(db: AsyncSession, slug: str):
        result = await db.execute(
            select(Workspace).where(Workspace.slug == slug)
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, workspace_id: UUID):
        result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_workspaces(db: AsyncSession, user_id: UUID):
        result = await db.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_user_workspace_by_id(
            db: AsyncSession,
            workspace_id: UUID,
            user_id: UUID,
    ):
        result = await db.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                Workspace.id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def add_workspace(db: AsyncSession, workspace: Workspace):
        db.add(workspace)

    @staticmethod
    async def add_membership(db: AsyncSession, membership: WorkspaceMember):
        db.add(membership)

    @staticmethod
    async def is_user_member(
            db: AsyncSession,
            workspace_id,
            user_id,
    ) -> bool:
        result = await db.execute(
            select(
                exists().where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == user_id,
                )
            )
        )
        return bool(result.scalar())

    @staticmethod
    async def delete_workspace(
            db: AsyncSession,
            workspace: Workspace,
    ) -> None:
        await db.delete(workspace)