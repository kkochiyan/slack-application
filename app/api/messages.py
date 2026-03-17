from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cuurent_user
from app.db.session import get_db
from app.schemas.message import MessageCreate, MessageResponse, MessageUpdate
from app.services.message_service import MessageService

router = APIRouter(tags=["Messages"])

@router.post(
    "/channels/{channel_id}/messages",
    response_model=MessageResponse,
)
async def create_message(
        channel_id: UUID,
        data: MessageCreate,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user)
):
    return await MessageService.create_message(
        db=db,
        current_user=current_user,
        channel_id=channel_id,
        content=data.content,
    )

@router.get(
    "/channels/{channel_id}/messages",
    response_model=list[MessageResponse],
)
async def list_messages(
        channel_id: UUID,
        limit: int = Query(default=50, ge=1, le=100),
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    return await MessageService.list_messages(
        db=db,
        current_user=current_user,
        channel_id=channel_id,
        limit=limit,
    )

@router.patch(
    "/messages/{message_id}",
    response_model=MessageResponse,
)
async def update_message(
        message_id: UUID,
        data: MessageUpdate,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    return await MessageService.update_message(
        db=db,
        current_user=current_user,
        message_id=message_id,
        content=data.content,
    )

@router.delete(
    "/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_message(
        message_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    await MessageService.delete_message(
        db=db,
        current_user=current_user,
        message_id=message_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)