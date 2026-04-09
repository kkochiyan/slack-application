from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace_member import WorkspaceMember
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository

class WorkspaceMemberService:

    @staticmethod
    async def add_member(
            db: AsyncSession,
            current_user,
            workspace_id: UUID,
            email: str,
    ) -> WorkspaceMember:
        requester_membership = await WorkspaceMemberRepository.get_by_workspace_and_user(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id
        )

        if not requester_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        if requester_membership.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace owner can add members",
            )

        normalized_email = email.strip().lower()

        target_user = await UserRepository.get_by_email(db, normalized_email)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        existing_membership = await WorkspaceMemberRepository.get_by_workspace_and_user(
            db=db,
            workspace_id=workspace_id,
            user_id=target_user.id,
        )
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this workspace",
            )

        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=target_user.id,
            role="member",
        )

        try:
            await WorkspaceMemberRepository.add(db, membership)
            await db.commit()
            await db.refresh(membership)
            return membership

        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this workspace",
            )

    @staticmethod
    async def list_members(
            db: AsyncSession,
            current_user,
            workspace_id: UUID,
    ) -> list[WorkspaceMember]:
        requester_membership = await WorkspaceMemberRepository.get_by_workspace_and_user(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
        if not requester_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        return await WorkspaceMemberRepository.get_workspace_members(
            db=db,
            workspace_id=workspace_id
        )

    @staticmethod
    async def remove_member(
            db: AsyncSession,
            current_user,
            workspace_id: UUID,
            user_id: UUID,
    ) -> None:
        requester_membership = await WorkspaceMemberRepository.get_by_workspace_and_user(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        if not requester_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        if requester_membership.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace owner can remove members",
            )

        target_membership = await WorkspaceMemberRepository.get_by_workspace_and_user(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if not target_membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace member not found",
            )

        if target_membership.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workspace owner cannot be removed",
            )

        await WorkspaceMemberRepository.delete(db, target_membership)
        await db.commit()

    @staticmethod
    async def leave_workspace(
            db: AsyncSession,
            current_user,
            workspace_id: UUID,
    ) -> None:
        membership = await WorkspaceMemberRepository.get_by_workspace_and_user(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        if membership.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workspace owner cannot leave the workspace",
            )

        await WorkspaceMemberRepository.delete(db, membership)
        await db.commit()