from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cuurent_user
from app.db.session import get_db
from app.schemas.workspace_member import WorkspaceMemberAdd, WorkspaceMemberResponse
from app.services.workspace_member_service import WorkspaceMemberService

router = APIRouter(tags=["Workspace Members"])

@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
)
async def add_workspace_member(
        workspace_id: UUID,
        data: WorkspaceMemberAdd,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    return await WorkspaceMemberService.add_member(
        db=db,
        current_user=current_user,
        workspace_id=workspace_id,
        user_id=data.user_id
    )

@router.get(
    "/workspaces/{workspace_id}/members",
    response_model=list[WorkspaceMemberResponse],
)
async def list_workspace_members(
        workspace_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    return await WorkspaceMemberService.list_members(
        db=db,
        current_user=current_user,
        workspace_id=workspace_id,
    )

@router.delete(
    "/workspaces/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_workspace_member(
        workspace_id: UUID,
        user_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    await WorkspaceMemberService.remove_member(
        db=db,
        current_user=current_user,
        workspace_id=workspace_id,
        user_id=user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

