from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_cuurent_user
from app.db.session import get_db
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
        data: WorkspaceCreate,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_cuurent_user),
):
    return await WorkspaceService.create_workspace(
        db=db,
        current_user=current_user,
        name=data.name,
        slug=data.slug,
    )

@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_cuurent_user),
):
    return await WorkspaceService.list_user_workspaces(
        db=db,
        current_user=current_user,
    )

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
        workspace_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user = Depends(get_cuurent_user),
):
    return await WorkspaceService.get_user_workspaces_by_id(
        db=db,
        workspace_id=workspace_id,
        current_user=current_user
    )