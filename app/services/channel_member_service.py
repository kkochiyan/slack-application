from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.channel_member import ChannelMember
from app.repositories.channel_member_repository import ChannelMemberRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository

class ChannelMemberService:
    @staticmethod
    async def add_member(
        db: AsyncSession,
        current_user,
        channel_id: UUID,
        email: str,
    ) -> dict:
        channel = await ChannelMemberService._get_channel_or_404(
            db=db,
            channel_id=channel_id,
        )
        ChannelMemberService._ensure_private_channel(
            channel=channel,
            detail="Members can only be managed explicitly for private channels",
        )
        await ChannelMemberService._ensure_workspace_member_or_404(
            db=db,
            workspace_id=channel.workspace_id,
            user_id=current_user.id,
            detail="Channel not found",
        )

        requester_membership = await ChannelMemberService._get_membership_or_403(
            db=db,
            channel_id=channel_id,
            user_id=current_user.id,
            detail="You do not have access to manage this channel",
        )
        ChannelMemberService._ensure_owner_role(
            membership=requester_membership,
            detail="Only channel owner can add members",
        )

        normalized_email = ChannelMemberService._normalize_email(email)
        target_user = await ChannelMemberService._get_user_by_email_or_404(
            db=db,
            email=normalized_email,
        )

        await ChannelMemberService._ensure_workspace_member_or_400(
            db=db,
            workspace_id=channel.workspace_id,
            user_id=target_user.id,
            detail="User is not a member of this workspace",
        )
        await ChannelMemberService._ensure_not_channel_member(
            db=db,
            channel_id=channel_id,
            user_id=target_user.id,
            detail="User is already a member of this channel",
        )

        membership = ChannelMember(
            channel_id=channel_id,
            user_id=target_user.id,
            role="member",
        )

        try:
            await ChannelMemberRepository.add(db, membership)
            await db.commit()
            await db.refresh(membership)
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this channel",
            )

        return await ChannelMemberService._get_created_member_or_500(
            db=db,
            channel_id=channel_id,
            membership_id=membership.id,
        )

    @staticmethod
    async def list_members(
        db: AsyncSession,
        current_user,
        channel_id: UUID,
    ) -> list[dict]:
        channel = await ChannelMemberService._get_channel_or_404(
            db=db,
            channel_id=channel_id,
        )
        ChannelMemberService._ensure_private_channel(
            channel=channel,
            detail="Explicit member list is only available for private channels",
        )
        await ChannelMemberService._ensure_channel_member_or_404(
            db=db,
            channel_id=channel_id,
            user_id=current_user.id,
            detail="Channel not found",
        )

        return await ChannelMemberRepository.get_channel_members(
            db,
            channel_id,
        )

    @staticmethod
    async def remove_member(
        db: AsyncSession,
        current_user,
        channel_id: UUID,
        user_id: UUID,
    ) -> None:
        channel = await ChannelMemberService._get_channel_or_404(
            db=db,
            channel_id=channel_id,
        )
        ChannelMemberService._ensure_private_channel(
            channel=channel,
            detail="Members can only be managed explicitly for private channels",
        )

        requester_membership = await ChannelMemberService._get_membership_or_403(
            db=db,
            channel_id=channel_id,
            user_id=current_user.id,
            detail="You do not have access to manage this channel",
        )
        ChannelMemberService._ensure_owner_role(
            membership=requester_membership,
            detail="Only channel owner can remove members",
        )

        membership = await ChannelMemberService._get_membership_or_404(
            db=db,
            channel_id=channel_id,
            user_id=user_id,
            detail="Channel member not found",
        )
        ChannelMemberService._ensure_not_owner_membership(
            membership=membership,
            detail="Channel owner cannot be removed",
        )

        await ChannelMemberRepository.delete(db, membership)
        await db.commit()

    @staticmethod
    async def leave_channel(
        db: AsyncSession,
        current_user,
        channel_id: UUID,
    ) -> None:
        channel = await ChannelMemberService._get_channel_or_404(
            db=db,
            channel_id=channel_id,
        )
        ChannelMemberService._ensure_private_channel(
            channel=channel,
            detail="You can leave only private channels",
        )

        membership = await ChannelMemberService._get_membership_or_404(
            db=db,
            channel_id=channel_id,
            user_id=current_user.id,
            detail="Channel member not found",
        )
        ChannelMemberService._ensure_not_owner_membership(
            membership=membership,
            detail="Channel owner cannot leave the channel",
        )

        await ChannelMemberRepository.delete(db, membership)
        await db.commit()

    @staticmethod
    async def _get_channel_or_404(
        db: AsyncSession,
        channel_id: UUID,
    ) -> Channel:
        channel = await ChannelRepository.get_by_id(db, channel_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )
        return channel

    @staticmethod
    def _ensure_private_channel(
        channel: Channel,
        detail: str,
    ) -> None:
        if not channel.is_private:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )

    @staticmethod
    async def _ensure_workspace_member_or_404(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
        detail: str,
    ) -> None:
        is_member = await WorkspaceRepository.is_user_member(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            )

    @staticmethod
    async def _ensure_workspace_member_or_400(
        db: AsyncSession,
        workspace_id: UUID,
        user_id: UUID,
        detail: str,
    ) -> None:
        is_member = await WorkspaceRepository.is_user_member(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )

    @staticmethod
    async def _ensure_channel_member_or_404(
        db: AsyncSession,
        channel_id: UUID,
        user_id: UUID,
        detail: str,
    ) -> None:
        is_member = await ChannelMemberRepository.is_user_member(
            db=db,
            channel_id=channel_id,
            user_id=user_id,
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            )

    @staticmethod
    async def _get_membership_or_404(
        db: AsyncSession,
        channel_id: UUID,
        user_id: UUID,
        detail: str,
    ) -> ChannelMember:
        membership = await ChannelMemberRepository.get_by_channel_and_user(
            db=db,
            channel_id=channel_id,
            user_id=user_id,
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            )
        return membership

    @staticmethod
    async def _get_membership_or_403(
        db: AsyncSession,
        channel_id: UUID,
        user_id: UUID,
        detail: str,
    ) -> ChannelMember:
        membership = await ChannelMemberRepository.get_by_channel_and_user(
            db=db,
            channel_id=channel_id,
            user_id=user_id,
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )
        return membership

    @staticmethod
    def _ensure_owner_role(
        membership: ChannelMember,
        detail: str,
    ) -> None:
        if membership.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )

    @staticmethod
    def _ensure_not_owner_membership(
        membership: ChannelMember,
        detail: str,
    ) -> None:
        if membership.role == "owner":
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
    async def _ensure_not_channel_member(
        db: AsyncSession,
        channel_id: UUID,
        user_id: UUID,
        detail: str,
    ) -> None:
        existing = await ChannelMemberRepository.get_by_channel_and_user(
            db=db,
            channel_id=channel_id,
            user_id=user_id,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            )

    @staticmethod
    async def _get_created_member_or_500(
        db: AsyncSession,
        channel_id: UUID,
        membership_id: UUID,
    ) -> dict:
        members = await ChannelMemberRepository.get_channel_members(
            db,
            channel_id,
        )

        for member in members:
            if member["id"] == membership_id:
                return member

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Created channel member could not be loaded",
        )