from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.repositories.channel_member_repository import ChannelMemberRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.workspace_repository import WorkspaceRepository

class MessageService:

    @staticmethod
    def _normalize_content(content: str) -> str:
        normalize_content = content.strip()

        if not normalize_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message can not be empty",
            )

        return normalize_content

    @staticmethod
    async def _ensure_channel_access(
            db: AsyncSession,
            current_user,
            channel_id: UUID,
    ):
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
    async def _get_accessible_message(
            db: AsyncSession,
            current_user,
            message_id: UUID,
    ) -> Message:
        message = await MessageRepository.get_by_id(db, message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        await MessageService._ensure_channel_access(
            db=db,
            current_user=current_user,
            channel_id=message.channel_id,
        )

        return message

    @staticmethod
    async def create_message(
            db: AsyncSession,
            current_user,
            channel_id: UUID,
            content: str,
    ) -> Message:
        await MessageService._ensure_channel_access(db, current_user, channel_id)

        normalized_content = MessageService._normalize_content(content)

        message = Message(
            channel_id=channel_id,
            author_id=current_user.id,
            content=normalized_content,
            message_type="text",
        )

        await MessageRepository.add(db, message)
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def list_messages(
            db: AsyncSession,
            current_user,
            channel_id: UUID,
            limit: int = 50,
    ) -> list[Message]:
        await MessageService._ensure_channel_access(db, current_user, channel_id)
        return await MessageRepository.get_channel_messages(
            db=db,
            channel_id=channel_id,
            limit=limit,
        )

    @staticmethod
    async def update_message(
            db: AsyncSession,
            current_user,
            message_id: UUID,
            content: str,
    ) -> Message:
        message = await MessageService._get_accessible_message(
            db=db,
            current_user=current_user,
            message_id=message_id,
        )

        if message.author_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can edit only your own messages",
            )

        if message.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deleted message cannot be edited",
            )

        normalized_content = MessageService._normalize_content(content)

        message.content = normalized_content
        message.edited_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def delete_message(
            db: AsyncSession,
            current_user,
            message_id: UUID,
    ) -> None:
        message = await MessageService._get_accessible_message(
            db=db,
            current_user=current_user,
            message_id=message_id,
        )

        if message.author_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can delete only your own messages",
            )

        if message.deleted_at is not None:
            return

        message.deleted_at = datetime.now(timezone.utc)
        await db.commit()