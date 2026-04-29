from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.workspaces import router as workspaces_router
from app.api.channels import router as channels_route
from app.api.channel_members import router as channel_members_router
from app.api.workspace_members import router as workspace_members_router
from app.api.messages import router as messages_router
from app.api.calls import router as calls_router
from app.services.message_service import MessageService

from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await MessageService.shutdown_pubsub_listener()

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(workspaces_router)
    app.include_router(channels_route)
    app.include_router(channel_members_router)
    app.include_router(workspace_members_router)
    app.include_router(messages_router)
    app.include_router(calls_router)

    @app.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        return {
            "message": f"{settings.app_name} is running",
            "environment": settings.app_env,
        }

    return app

app = create_application()