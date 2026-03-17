from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cuurent_user
from app.db.session import get_db
from app.schemas.channel import ChannelResponse, ChannelCreate
from app.services.channel_service import ChannelService

router = APIRouter(tags=["Channels"])

@router.post(
    "/workspaces/{workspace_id}/channels",
    response_model=ChannelResponse,
)
async def create_channel(
        workspace_id: UUID,
        data: ChannelCreate,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    return await ChannelService.create_channel(
        db=db,
        current_user=current_user,
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        is_private=data.is_private
    )

@router.get(
    "/workspaces/{workspace_id}/channels",
    response_model=list[ChannelResponse],
)
async def list_channels(
        workspace_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    return await ChannelService.list_workspace_channels(
        db=db,
        current_user=current_user,
        workspace_id=workspace_id,
    )

@router.get(
    "/channels/{channel_id}",
    response_model=ChannelResponse,
)
async def get_channel(
        channel_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    return await ChannelService.get_channel_by_id(
        db=db,
        current_user=current_user,
        channel_id=channel_id,
    )

