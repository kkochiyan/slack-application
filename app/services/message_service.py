import asyncio
from collections import defaultdict
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
    _pubsub = None
    _listener_task: asyncio.Task | None = None
    _waiters: dict[str, set[asyncio.Event]] = defaultdict(set)
    _listener_lock = asyncio.Lock()

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
    async def _ensure_message_belongs_to_channel(
        db: AsyncSession,
        current_user,
        message_id: UUID,
        channel_id: UUID,
        field_name: str,
    ) -> None:
        message = await MessageService._get_accessible_message(
            db=db,
            current_user=current_user,
            message_id=message_id,
        )
        if message.channel_id != channel_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{field_name}' message does not belong to this channel",
            )

    @staticmethod
    async def _publish_channel_message_event(
        channel_id: UUID,
        message_id: UUID,
    ) -> None:
        await redis_client.publish(
            channel_messages_topic(str(channel_id)),
            str(message_id),
        )

    @staticmethod
    def _find_message_in_payload_or_500(
        messages: list[dict],
        message_id: UUID,
        detail: str,
    ) -> dict:
        for item in messages:
            if item["id"] == message_id:
                return item

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )

    @staticmethod
    async def _ensure_pubsub_listener_started() -> None:
        listener_running = (
            MessageService._listener_task is not None
            and not MessageService._listener_task.done()
        )
        if listener_running:
            return

        async with MessageService._listener_lock:
            listener_running = (
                MessageService._listener_task is not None
                and not MessageService._listener_task.done()
            )
            if listener_running:
                return

            MessageService._pubsub = redis_client.pubsub()
            await MessageService._pubsub.psubscribe("channel:*:messages")
            MessageService._listener_task = asyncio.create_task(
                MessageService._pubsub_listener_loop()
            )

    @staticmethod
    async def _pubsub_listener_loop() -> None:
        try:
            while True:
                message = await MessageService._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message is None:
                    await asyncio.sleep(0.1)
                    continue

                topic = message.get("channel")

                if isinstance(topic, bytes):
                    topic = topic.decode()

                if not isinstance(topic, str):
                    continue

                waiters = MessageService._waiters.get(topic)
                if not waiters:
                    continue

                for event in list(waiters):
                    event.set()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Message pubsub listener error: {e}")

    @staticmethod
    async def _wait_for_channel_message(
        channel_id: UUID,
        timeout_seconds: int,
    ) -> None:
        await MessageService._ensure_pubsub_listener_started()

        topic = channel_messages_topic(str(channel_id))
        event = asyncio.Event()
        MessageService._waiters[topic].add(event)

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
        except TimeoutError:
            pass
        finally:
            MessageService._waiters[topic].discard(event)
            if not MessageService._waiters[topic]:
                MessageService._waiters.pop(topic, None)

    @staticmethod
    async def shutdown_pubsub_listener() -> None:
        if MessageService._listener_task is not None:
            MessageService._listener_task.cancel()
            try:
                await MessageService._listener_task
            except asyncio.CancelledError:
                pass
            MessageService._listener_task = None

        if MessageService._pubsub is not None:
            await MessageService._pubsub.punsubscribe("channel:*:messages")
            await MessageService._pubsub.aclose()
            MessageService._pubsub = None

    @staticmethod
    async def create_message(
        db: AsyncSession,
        current_user,
        channel_id: UUID,
        content: str,
    ) -> dict:
        await MessageService._ensure_channel_access(
            db=db,
            current_user=current_user,
            channel_id=channel_id,
        )

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

        await MessageService._publish_channel_message_event(
            channel_id=channel_id,
            message_id=message.id,
        )

        result = await MessageRepository.get_channel_messages(
            db=db,
            channel_id=channel_id,
            limit=1,
            after=message.id,
        )

        if result:
            return result[0]

        result = await MessageRepository.get_channel_messages(
            db=db,
            channel_id=channel_id,
            limit=50,
        )
        return MessageService._find_message_in_payload_or_500(
            messages=result,
            message_id=message.id,
            detail="Created message could not be loaded",
        )

    @staticmethod
    async def list_messages(
        db: AsyncSession,
        current_user,
        channel_id: UUID,
        limit: int = 50,
        before: UUID | None = None,
        after: UUID | None = None,
    ) -> list[dict]:
        await MessageService._ensure_channel_access(
            db=db,
            current_user=current_user,
            channel_id=channel_id,
        )

        if before and after:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot use 'before' and 'after' together",
            )

        if before:
            await MessageService._ensure_message_belongs_to_channel(
                db=db,
                current_user=current_user,
                message_id=before,
                channel_id=channel_id,
                field_name="before",
            )

        if after:
            await MessageService._ensure_message_belongs_to_channel(
                db=db,
                current_user=current_user,
                message_id=after,
                channel_id=channel_id,
                field_name="after",
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
    ) -> dict:
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

        await MessageService._publish_channel_message_event(
            channel_id=message.channel_id,
            message_id=message.id,
        )

        result = await MessageRepository.get_channel_messages(
            db=db,
            channel_id=message.channel_id,
            limit=50,
        )
        return MessageService._find_message_in_payload_or_500(
            messages=result,
            message_id=message.id,
            detail="Updated message could not be loaded",
        )

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

        await MessageService._publish_channel_message_event(
            channel_id=message.channel_id,
            message_id=message.id,
        )

    @staticmethod
    async def long_poll_messages(
        db: AsyncSession,
        current_user,
        channel_id: UUID,
        after: UUID | None = None,
        timeout_seconds: int = 20,
    ) -> list[dict]:
        await MessageService._ensure_channel_access(
            db=db,
            current_user=current_user,
            channel_id=channel_id,
        )

        if after:
            await MessageService._ensure_message_belongs_to_channel(
                db=db,
                current_user=current_user,
                message_id=after,
                channel_id=channel_id,
                field_name="after",
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

        await MessageService._wait_for_channel_message(
            channel_id=channel_id,
            timeout_seconds=timeout_seconds,
        )

        return await MessageRepository.get_channel_messages(
            db=db,
            channel_id=channel_id,
            before=None,
            after=after,
            limit=50,
        )