from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
    ) -> ChannelMember:
        channel = await ChannelRepository.get_by_id(db, channel_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        if not channel.is_private:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Members can only be managed explicitly for private channels",
            )

        requester_is_workspace_member = await WorkspaceRepository.is_user_member(
            db=db,
            workspace_id=channel.workspace_id,
            user_id=current_user.id,
        )
        if not requester_is_workspace_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        requester_membership = await ChannelMemberRepository.get_by_channel_and_user(
            db=db,
            channel_id=channel_id,
            user_id=current_user.id,
        )
        if not requester_membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to manage this channel",
            )

        if requester_membership.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only channel owner can add members",
            )

        normalized_email = email.strip().lower()

        target_user = await UserRepository.get_by_email(db, normalized_email)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        target_is_workspace_member = await WorkspaceRepository.is_user_member(
            db=db,
            workspace_id=channel.workspace_id,
            user_id=target_user.id,
        )
        if not target_is_workspace_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a member of this workspace",
            )

        existing = await ChannelMemberRepository.get_by_channel_and_user(
            db=db,
            channel_id=channel_id,
            user_id=target_user.id,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
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
            return membership

        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this channel",
            )

    @staticmethod
    async def list_members(
        db: AsyncSession,
        current_user,
        channel_id: UUID,
    ) -> list[ChannelMember]:
        channel = await ChannelRepository.get_by_id(db, channel_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        if not channel.is_private:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explicit member list is only available for private channels",
            )

        is_channel_member = await ChannelMemberRepository.is_user_member(
            db=db,
            channel_id=channel_id,
            user_id=current_user.id,
        )

        if not is_channel_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
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
        channel = await ChannelRepository.get_by_id(db, channel_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        if not channel.is_private:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Members can only be managed explicitly for private channels",
            )

        requester_membership = await ChannelMemberRepository.get_by_channel_and_user(
            db=db,
            channel_id=channel_id,
            user_id=current_user.id,
        )
        if not requester_membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to manage this channel",
            )

        if requester_membership.role != "owner":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only channel owner can remove members",
            )

        membership = await ChannelMemberRepository.get_by_channel_and_user(
            db=db,
            channel_id=channel_id,
            user_id=user_id,
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel member not found",
            )

        if membership.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
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
        channel = await ChannelRepository.get_by_id(db, channel_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        if not channel.is_private:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can leave only private channels",
            )

        membership = await ChannelMemberRepository.get_by_channel_and_user(
            db=db,
            channel_id=channel_id,
            user_id=current_user.id,
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel member not found",
            )

        if membership.role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel owner cannot leave the channel",
            )

        await ChannelMemberRepository.delete(db, membership)
        await db.commit()