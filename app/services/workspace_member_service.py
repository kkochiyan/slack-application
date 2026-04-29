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
    ) -> dict:
        requester_membership = await WorkspaceMemberService._get_workspace_membership_or_404(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        WorkspaceMemberService._ensure_owner_role(
            requester_membership.role,
            detail="Only workspace owner can add members",
        )

        normalized_email = WorkspaceMemberService._normalize_email(email)

        target_user = await WorkspaceMemberService._get_user_by_email_or_404(
            db=db,
            email=normalized_email,
        )

        await WorkspaceMemberService._ensure_not_workspace_member(
            db=db,
            workspace_id=workspace_id,
            user_id=target_user.id,
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
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this workspace",
            )

        return await WorkspaceMemberService._get_created_member_or_500(
            db=db,
            workspace_id=workspace_id,
            membership_id=membership.id,
        )

    @staticmethod
    async def list_members(
        db: AsyncSession,
        current_user,
        workspace_id: UUID,
    ) -> list[dict]:
        await WorkspaceMemberService._get_workspace_membership_or_404(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        return await WorkspaceMemberRepository.get_workspace_members(
            db=db,
            workspace_id=workspace_id,
        )

    @staticmethod
    async def remove_member(
        db: AsyncSession,
        current_user,
        workspace_id: UUID,
        user_id: UUID,
    ) -> None:
        requester_membership = await WorkspaceMemberService._get_workspace_membership_or_404(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        WorkspaceMemberService._ensure_owner_role(
            requester_membership.role,
            detail="Only workspace owner can remove members",
        )

        target_membership = await WorkspaceMemberService._get_workspace_membership_or_404(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            detail="Workspace member not found",
        )

        WorkspaceMemberService._ensure_not_owner_membership(
            target_membership.role,
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
        membership = await WorkspaceMemberService._get_workspace_membership_or_404(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        WorkspaceMemberService._ensure_not_owner_membership(
            membership.role,
            detail="Workspace owner cannot leave the workspace",
        )

        await WorkspaceMemberRepository.delete(db, membership)
        await db.commit()

    # ========================
    # Helpers
    # ========================

    @staticmethod
    async def _get_workspace_membership_or_404(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
        detail: str = "Workspace not found",
    ):
        membership = await WorkspaceMemberRepository.get_by_workspace_and_user(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            )
        return membership

    @staticmethod
    def _ensure_owner_role(
        role: str,
        detail: str,
    ) -> None:
        if role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )

    @staticmethod
    def _ensure_not_owner_membership(
        role: str,
        detail: str,
    ) -> None:
        if role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    async def _get_user_by_email_or_404(
        db: AsyncSession,
        email: str,
    ):
        user = await UserRepository.get_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    @staticmethod
    async def _ensure_not_workspace_member(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
    ) -> None:
        existing = await WorkspaceMemberRepository.get_by_workspace_and_user(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this workspace",
            )

    @staticmethod
    async def _get_created_member_or_500(
        db: AsyncSession,
        workspace_id: UUID,
        membership_id: UUID,
    ) -> dict:
        members = await WorkspaceMemberRepository.get_workspace_members(
            db,
            workspace_id,
        )

        for m in members:
            if m["id"] == membership_id:
                return m

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Created member not found",
        )