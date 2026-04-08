import asyncio
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import redis_client, channel_messages_topic
from app.models.message import Message
from app.repositories.channel_member_repository import ChannelMemberRepository
from app.repositories.channel_repository import ChannelRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.workspace_repository import WorkspaceRepository


class MessageService:
    @staticmethod
    def _normalize_content(content: str) -> str:
        normalized_content = content.strip()

        if not normalized_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message can not be empty",
            )

        return normalized_content

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

        await redis_client.publish(
            channel_messages_topic(str(channel_id)),
            str(message.id),
        )

        return message

    @staticmethod
    async def list_messages(
        db: AsyncSession,
        current_user,
        channel_id: UUID,
        limit: int = 50,
        before: UUID | None = None,
        after: UUID | None = None,
    ) -> list[Message]:
        await MessageService._ensure_channel_access(db, current_user, channel_id)

        if before and after:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot use 'before' and 'after' together",
            )

        if before:
            before_message = await MessageService._get_accessible_message(
                db=db,
                current_user=current_user,
                message_id=before,
            )
            if before_message.channel_id != channel_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="'before' message does not belong to this channel",
                )

        if after:
            after_message = await MessageService._get_accessible_message(
                db=db,
                current_user=current_user,
                message_id=after,
            )
            if after_message.channel_id != channel_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="'after' message does not belong to this channel",
                )

        return await MessageRepository.get_channel_messages(
            db=db,
            channel_id=channel_id,
            limit=limit,
            before=before,
            after=after,
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
        await redis_client.publish(
            channel_messages_topic(str(message.channel_id)),
            str(message.id),
        )
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
        await redis_client.publish(
            channel_messages_topic(str(message.channel_id)),
            str(message.id),
        )

    @staticmethod
    async def long_poll_messages(
        db: AsyncSession,
        current_user,
        channel_id: UUID,
        after: UUID | None = None,
        timeout_seconds: int = 20,
    ) -> list[Message]:
        await MessageService._ensure_channel_access(
            db=db,
            current_user=current_user,
            channel_id=channel_id,
        )

        if after:
            after_message = await MessageService._get_accessible_message(
                db=db,
                current_user=current_user,
                message_id=after,
            )
            if after_message.channel_id != channel_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="'after' message does not belong to this channel",
                )

        messages = await MessageRepository.get_channel_messages(
            db=db,
            channel_id=channel_id,
            before=None,
            after=after,
            limit=50,
        )

        if messages:
            return messages

        pubsub = redis_client.pubsub()
        topic = channel_messages_topic(str(channel_id))
        await pubsub.subscribe(topic)

        try:
            try:
                async with asyncio.timeout(timeout_seconds):
                    while True:
                        event = await pubsub.get_message(
                            ignore_subscribe_messages=True,
                            timeout=1.0,
                        )
                        if event is not None:
                            break

                        await asyncio.sleep(0.1)
            except TimeoutError:
                return []

            messages = await MessageRepository.get_channel_messages(
                db=db,
                channel_id=channel_id,
                before=None,
                after=after,
                limit=50,
            )

            return messages

        finally:
            await pubsub.unsubscribe(topic)
            await pubsub.aclose()