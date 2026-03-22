from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.workspace_repository import WorkspaceRepository

class WorkspaceService:

    @staticmethod
    async def create_workspace(
            db: AsyncSession,
            current_user,
            name: str,
            slug: str
    ) -> Workspace:
        normalized_slug = slug.strip().lower()

        existing = await WorkspaceRepository.get_by_slug(db, normalized_slug)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Workspace with this slug already exists",
            )

        workspace = Workspace(
            name=name.strip(),
            slug=normalized_slug,
            owner_id=current_user.id,
        )

        try:
            db.add(workspace)
            await db.flush()

            membership = WorkspaceMember(
                workspace_id=workspace.id,
                user_id=current_user.id,
                role="owner",
            )

            db.add(membership)

            await db.commit()
            await db.refresh(workspace)

            return workspace

        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Workspace with this slug already exists",
            )

    @staticmethod
    async def list_user_workspaces(
            db: AsyncSession,
            current_user,
    ) -> list[Workspace]:
        return await WorkspaceRepository.get_user_workspaces(db, current_user.id)

    @staticmethod
    async def get_user_workspaces_by_id(
            db: AsyncSession,
            workspace_id: UUID,
            current_user,
    ) -> Workspace:
        workspace = await WorkspaceRepository.get_user_workspace_by_id(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )

        return workspace

    @staticmethod
    async def delete_workspace(
            db: AsyncSession,
            current_user,
            workspace_id: UUID,
    ) -> None:
        workspace = await WorkspaceRepository.get_by_id(db, workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        if workspace.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace owner can delete workspace",
            )

        await WorkspaceRepository.delete_workspace(db, workspace)
        await db.commit()