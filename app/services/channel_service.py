from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.channel_member import ChannelMember
from app.repositories.channel_member_repository import ChannelMemberRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository

class ChannelService:

    @staticmethod
    async def create_channel(
            db: AsyncSession,
            current_user,
            workspace_id: UUID,
            name: str,
            description: str | None,
            is_private: bool,
    ) -> Channel:
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
                detail="Only workspace owner can create channels",
            )

        normalized_name = name.strip().lower()

        existing = await ChannelRepository.get_by_workspace_and_name(
            db=db,
            workspace_id=workspace_id,
            name=normalized_name,
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Channel with this name is already exists in workspace",
            )

        channel = Channel(
            workspace_id=workspace_id,
            name=normalized_name,
            description=description.strip() if description else None,
            is_private=is_private,
            created_by=current_user.id
        )

        try:
            db.add(channel)
            await db.flush()

            if is_private:
                membership = ChannelMember(
                    channel_id=channel.id,
                    user_id=current_user.id,
                    role="owner",
                )
                db.add(membership)

            await db.commit()
            await db.refresh(channel)
            return channel

        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Channel with this name already exists in workspace",
            )

    @staticmethod
    async def list_workspace_channels(
            db: AsyncSession,
            current_user,
            workspace_id: UUID,
    ) -> list[Channel]:
        is_workspace_member = await WorkspaceRepository.is_user_member(db, workspace_id, current_user.id)

        if not is_workspace_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        channels = await ChannelRepository.get_workspace_channels(
            db=db,
            workspace_id=workspace_id,
        )

        visible_channels: list[Channel] = []

        for channel in channels:
            if not channel.is_private:
                visible_channels.append(channel)
                continue

            is_channel_member = await ChannelMemberRepository.is_user_member(
                db=db,
                channel_id=channel.id,
                user_id=current_user.id,
            )

            if is_channel_member:
                visible_channels.append(channel)

        return visible_channels

    @staticmethod
    async def get_channel_by_id(
            db: AsyncSession,
            current_user,
            channel_id: UUID
    ) -> Channel:
        channel = await ChannelRepository.get_by_id(db, channel_id)

        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        is_workspace_member = await WorkspaceRepository.is_user_member(
            db=db,
            workspace_id=channel.workspace_id,
            user_id=current_user.id
        )

        if not is_workspace_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        if channel.is_private:
            is_channel_member = await ChannelMemberRepository.is_user_member(
                db=db,
                channel_id=channel.id,
                user_id=current_user.id,
            )
            if not is_channel_member:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Channel not found",
                )

        return channel

    @staticmethod
    async def delete_channel(
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

        is_workspace_member = await WorkspaceRepository.is_user_member(
            db=db,
            workspace_id=channel.workspace_id,
            user_id=current_user.id,
        )
        if not is_workspace_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        if channel.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only channel creator can delete channel",
            )

        await ChannelRepository.delete_channel(db, channel)
        await db.commit()