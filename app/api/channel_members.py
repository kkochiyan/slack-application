from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cuurent_user
from app.db.session import get_db
from app.schemas.channel_member import ChannelMemberAdd, ChannelMemberResponse
from app.services.channel_member_service import ChannelMemberService

router = APIRouter(tags=["Channel Members"])

@router.post(
    "/channels/{channel_id}/members",
    response_model=ChannelMemberResponse,
)
async def get_channel_member(
        channel_id: UUID,
        data: ChannelMemberAdd,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user)
):
    return await ChannelMemberService.add_member(
        db=db,
        current_user=current_user,
        channel_id=channel_id,
        user_id=data.user_id,
    )

@router.get(
    "/channels/{channel_id}/members",
    response_model=list[ChannelMemberResponse],
)
async def list_channels_members(
        channel_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    return await ChannelMemberService.list_members(
        db=db,
        current_user=current_user,
        channel_id=channel_id,
    )

@router.delete(
    "/channels/{channel_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_channel_member(
        channel_id: UUID,
        user_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    await ChannelMemberService.remove_member(
        db=db,
        current_user=current_user,
        channel_id=channel_id,
        user_id=user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)